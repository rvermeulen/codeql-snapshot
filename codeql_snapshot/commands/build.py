import click
from sqlalchemy import select
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import Session
from typing import Optional, List
from codeql_snapshot.models import Snapshot, SnapshotState
from codeql_snapshot.helpers.object_store import (
    has_source_object,
    get_source_object,
    create_database_object,
)
from codeql_snapshot.helpers.zip import zipdir
from codeql_snapshot.helpers.codeql import CodeQL, CodeQLException
from tempfile import TemporaryDirectory
from pathlib import Path
from zipfile import ZipFile
from subprocess import run
import shlex


@click.command(name="build")
@click.option("-s", "--snapshot-global-id")
@click.option("-c", "--command")
@click.option("-x", "--exec")
@click.option("-r", "--retry", is_flag=True)
@click.option("-l", "--label", multiple=True, default=["default"])
@click.pass_context
def command(
    ctx: click.Context,
    snapshot_global_id: Optional[str],
    command: Optional[str],
    exec: Optional[str],
    retry: bool,
    label: List[str],
):

    if command and exec:
        raise click.exceptions.UsageError("Cannot use both command and exec!")

    database_engine: Engine = ctx.obj["database"]["engine"]

    global_id: Optional[str] = None
    source_id: Optional[str] = None
    language: Optional[str] = None
    with Session(database_engine) as session, session.begin():

        stmt = select(Snapshot).where(Snapshot.label == label)

        if snapshot_global_id:
            stmt = stmt.where(
                Snapshot.global_id == snapshot_global_id
            ).with_for_update()
        else:
            stmt = stmt.limit(1).with_for_update(skip_locked=True)

        if retry:
            stmt = stmt.where(Snapshot.state == SnapshotState.BUILD_FAILED)
        else:
            stmt = stmt.where(Snapshot.state == SnapshotState.NOT_BUILT)

        snapshot = session.scalar(stmt)
        if snapshot:
            snapshot.state = SnapshotState.BUILD_IN_PROGRESS

            global_id = snapshot.global_id
            source_id = snapshot.source_id
            language = snapshot.language.value

    if global_id and source_id and language:
        if has_source_object(ctx, source_id):
            with TemporaryDirectory() as tmpdir:
                tmpzip = (Path(tmpdir) / source_id).with_suffix(".zip")

                get_source_object(ctx, source_id, tmpzip)

                tmp_source_root: Path = Path(tmpdir) / source_id
                tmp_source_root.mkdir()

                with ZipFile(str(tmpzip)) as zipfile:
                    zipfile.extractall(tmp_source_root)

                database_path = Path(tmpdir, f"{global_id}-db")
                codeql = CodeQL()
                try:
                    if command:
                        codeql.database_create(
                            language,
                            tmp_source_root,
                            database_path,
                            command=command,
                        )
                    elif exec:
                        args = shlex.split(exec) + [
                            language,
                            str(tmp_source_root),
                            str(database_path),
                        ]

                        try:
                            cp = run(args)
                            if cp.returncode != 0:
                                raise CodeQLException("custom build execution failed!")
                        except OSError as e:
                            raise CodeQLException(
                                f"Failed to execute custom build command with error: {e.strerror}!"
                            )
                    else:
                        codeql.database_create(language, tmp_source_root, database_path)

                    bundle_path = codeql.database_bundle(database_path)
                    create_database_object(ctx, global_id, bundle_path)
                    newstate = SnapshotState.NOT_ANALYZED
                except CodeQLException as e:
                    if database_path.exists():
                        zipped_database_path = database_path.with_suffix(".zip")
                        zipdir(database_path, zipped_database_path)
                        create_database_object(ctx, global_id, zipped_database_path)

                    newstate = SnapshotState.BUILD_FAILED

                    click.echo(f"Failed to create database with error {e}")

        else:
            newstate = SnapshotState.SNAPSHOT_FAILED

        with Session(database_engine) as session, session.begin():

            stmt = (
                select(Snapshot)
                .where(Snapshot.global_id == global_id)
                .with_for_update()
            )

            snapshot = session.scalar(stmt)
            if snapshot:
                snapshot.state = newstate
            else:
                click.echo(
                    f"Could not find snapshot to update state from {SnapshotState.BUILD_IN_PROGRESS} to {newstate}!"
                )
    else:
        click.echo("Could not find snapshot to build!")
