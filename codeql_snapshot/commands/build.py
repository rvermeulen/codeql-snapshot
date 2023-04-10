import click
from sqlalchemy import select
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import Session
from typing import Optional
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
@click.pass_context
def command(
    ctx: click.Context,
    snapshot_global_id: Optional[str],
    command: Optional[str],
    exec: Optional[str],
):

    if command and exec:
        raise click.exceptions.UsageError("Cannot use both command and exec!")

    database_engine: Engine = ctx.obj["database"]["engine"]

    with Session(database_engine) as session, session.begin():

        if snapshot_global_id:
            stmt = (
                select(Snapshot)
                .where(Snapshot.global_id == snapshot_global_id)
                .where(Snapshot.state == SnapshotState.NOT_BUILT)
                .with_for_update()
            )

        else:
            stmt = (
                select(Snapshot)
                .where(Snapshot.state == SnapshotState.NOT_BUILT)
                .limit(1)
                .with_for_update()
            )

        snapshot = session.scalar(stmt)
        if snapshot:
            with session.begin_nested():
                snapshot.state = SnapshotState.BUILD_IN_PROGRESS

            if has_source_object(ctx, snapshot):
                with TemporaryDirectory() as tmpdir:
                    tmpzip = (Path(tmpdir) / snapshot.global_id).with_suffix(".zip")

                    get_source_object(ctx, snapshot, tmpzip)

                    tmp_source_root: Path = Path(tmpdir) / snapshot.global_id
                    tmp_source_root.mkdir()

                    with ZipFile(str(tmpzip)) as zipfile:
                        zipfile.extractall(tmp_source_root)

                    database_path = Path(
                        tmpdir, f"{snapshot.global_id}-{snapshot.language.value}-db"
                    )
                    codeql = CodeQL()
                    try:
                        if command:
                            codeql.database_create(
                                snapshot.language.value,
                                tmp_source_root,
                                database_path,
                                command=command,
                            )
                        elif exec:
                            args = shlex.split(exec) + [
                                snapshot.language.value,
                                str(tmp_source_root),
                                str(database_path),
                            ]

                            cp = run(args)
                            if cp.returncode != 0:
                                raise CodeQLException("custom build execution failed!")
                        else:
                            codeql.database_create(
                                snapshot.language.value, tmp_source_root, database_path
                            )

                        bundle_path = codeql.database_bundle(database_path)
                        create_database_object(ctx, snapshot, bundle_path)
                        snapshot.state = SnapshotState.NOT_ANALYZED
                    except CodeQLException as e:
                        if database_path.exists():
                            zipped_database_path = database_path.with_suffix(".zip")
                            zipdir(database_path, zipped_database_path)
                            create_database_object(ctx, snapshot, zipped_database_path)

                        snapshot.state = SnapshotState.BUILD_FAILED

                        click.echo(f"Failed to create database with error {e}")

            else:
                snapshot.state = SnapshotState.SNAPSHOT_FAILED
        else:
            click.echo("Could not find snapshot to build!")
