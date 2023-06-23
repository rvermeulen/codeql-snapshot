import click
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from typing import Optional, List
from codeql_snapshot.helpers.codeql import CodeQL, CodeQLException
from codeql_snapshot.helpers.object_store import (
    has_database_object,
    get_database_object,
    create_sarif_object,
)
from codeql_snapshot.models.snapshot import Snapshot, SnapshotState
from tempfile import TemporaryDirectory
from pathlib import Path


@click.command(name="analyze")
@click.option("-s", "--snapshot-global-id")
@click.option("-r", "--retry", is_flag=True)
@click.option("-l", "--label", multiple=True, default=["default"])
@click.pass_context
def command(ctx: click.Context, snapshot_global_id: Optional[str], retry: bool, label: List[str]) -> None:
    database_engine: Engine = ctx.obj["database"]["engine"]

    global_id: Optional[str] = None
    with Session(database_engine) as session, session.begin():
        stmt = select(Snapshot).where(Snapshot.label == label)

        if snapshot_global_id:
            stmt = stmt.where(
                Snapshot.global_id == snapshot_global_id
            ).with_for_update()
        else:
            stmt = stmt.limit(1).with_for_update(skip_locked=True)

        if retry:
            stmt = stmt.where(Snapshot.state == SnapshotState.ANALYSIS_FAILED)
        else:
            stmt = stmt.where(Snapshot.state == SnapshotState.NOT_ANALYZED)

        snapshot = session.scalar(stmt)
        if snapshot:
            snapshot.state = SnapshotState.ANALYSIS_IN_PROGRESS
            global_id = snapshot.global_id

    if global_id:
        if has_database_object(ctx, global_id):
            with TemporaryDirectory() as tmpdir:
                tmpzip = (Path(tmpdir) / global_id).with_suffix(".zip")

                get_database_object(ctx, global_id, tmpzip)

                try:
                    codeql = CodeQL()

                    codeql.database_unbundle(tmpzip)
                    database_path = tmpzip.with_suffix("")
                    sarif_path = database_path.with_suffix(".sarif")

                    codeql.database_analyze(database_path, sarif_path)
                    create_sarif_object(ctx, global_id, sarif_path)

                    newstate = SnapshotState.ANALYZED
                except CodeQLException as e:
                    newstate = SnapshotState.ANALYSIS_FAILED
                    click.echo(f"Failed to create database with error {e}")
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
                        f"Could not find snapshot to update state from {SnapshotState.ANALYSIS_IN_PROGRESS} to {newstate}!"
                    )
    else:
        click.echo("No snapshot requiring analysis!")
