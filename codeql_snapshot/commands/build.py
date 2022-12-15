import click
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from typing import Optional
from models import Snapshot, SnapshotState
from helpers.object_store import (
    has_source_object,
    get_source_object,
    create_database_object,
)
from helpers.zip import zipdir
from helpers.codeql import CodeQL, CodeQLException
from tempfile import TemporaryDirectory
from pathlib import Path
from zipfile import ZipFile


@click.command(name="build")
@click.option("-s", "--snapshot-global-id")
@click.option("-c", "--command")
@click.pass_context
def command(
    ctx: click.Context, snapshot_global_id: Optional[str], command: Optional[str]
):
    database_engine: Engine = ctx.obj["database"]["engine"]

    with Session(database_engine) as session:

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
            snapshot.state = SnapshotState.BUILD_IN_PROGRESS
            session.commit()

            if has_source_object(ctx, snapshot):
                with TemporaryDirectory() as tmpdir:
                    tmpzip = (Path(tmpdir) / snapshot.global_id).with_suffix(".zip")

                    get_source_object(ctx, snapshot, tmpzip)

                    tmp_source_root = Path(tmpdir) / snapshot.global_id
                    tmp_source_root.mkdir()

                    with ZipFile(str(tmpzip)) as zipfile:
                        zipfile.extractall(tmp_source_root)

                    database_path = Path(
                        tmpdir, f"{snapshot.global_id}-{snapshot.language.value}-db"
                    )
                    codeql = CodeQL()
                    try:
                        codeql.database_create(
                            snapshot.language.value, tmp_source_root, database_path
                        )

                        bundle_path = codeql.database_bundle(database_path)
                        create_database_object(ctx, snapshot, bundle_path)
                        snapshot.state = SnapshotState.NOT_ANALYZED
                        session.commit()
                    except CodeQLException as e:
                        if database_path.exists():
                            zipped_database_path = database_path.with_suffix(".zip")
                            zipdir(database_path, zipped_database_path)
                            create_database_object(ctx, snapshot, zipped_database_path)

                        snapshot.state = SnapshotState.BUILD_FAILED
                        session.commit()

                        click.echo(f"Failed to create database with error {e}")

            else:
                snapshot.state = SnapshotState.SNAPSHOT_FAILED
                session.commit()
        else:
            click.echo("Could not find snapshot to build!")
