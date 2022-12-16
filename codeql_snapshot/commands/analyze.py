import click
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from typing import Optional
from helpers.codeql import CodeQL, CodeQLException
from helpers.object_store import (
    has_database_object,
    get_database_object,
    create_sarif_object,
)
from models.snapshot import Snapshot, SnapshotState
from tempfile import TemporaryDirectory
from pathlib import Path


@click.command(name="analyze")
@click.option("-s", "--snapshot-global-id")
@click.option("-r", "--retry", is_flag=True)
@click.pass_context
def command(ctx: click.Context, snapshot_global_id: Optional[str], retry: bool) -> None:
    database_engine: Engine = ctx.obj["database"]["engine"]

    with Session(database_engine) as session:
        stmt = select(Snapshot).with_for_update()

        if snapshot_global_id:
            stmt = stmt.where(Snapshot.global_id == snapshot_global_id)
        else:
            stmt = stmt.limit(1)

        if retry:
            stmt = stmt.where(Snapshot.state == SnapshotState.ANALYSIS_FAILED)
        else:
            stmt = stmt.where(Snapshot.state == SnapshotState.NOT_ANALYZED)

        snapshot = session.scalar(stmt)
        if snapshot:
            snapshot.state = SnapshotState.ANALYSIS_IN_PROGRESS
            session.commit()

            if has_database_object(ctx, snapshot):
                with TemporaryDirectory() as tmpdir:
                    tmpzip = (Path(tmpdir) / snapshot.global_id).with_suffix(".zip")

                    get_database_object(ctx, snapshot, tmpzip)

                    try:
                        codeql = CodeQL()

                        codeql.database_unbundle(tmpzip)
                        database_path = tmpzip.with_suffix("")
                        sarif_path = database_path.with_suffix(".sarif")

                        codeql.database_analyze(database_path, sarif_path)
                        create_sarif_object(ctx, snapshot, sarif_path)

                        snapshot.state = SnapshotState.ANALYZED
                        session.commit()
                    except CodeQLException as e:
                        snapshot.state = SnapshotState.ANALYSIS_FAILED
                        session.commit()

                        click.echo(f"Failed to create database with error {e}")
                        input("Click to continue")

        else:
            click.echo("No snapshot requiring analysis!")
