import click
from sqlalchemy import Engine, select, func
from sqlalchemy.orm import Session
from codeql_snapshot.helpers.object_store import (
    has_database_object,
    remove_database_object,
    has_sarif_object,
    remove_sarif_object,
    has_source_object,
    remove_source_object,
)
from codeql_snapshot.models.snapshot import Snapshot


@click.command(name="delete")
@click.option("-s", "--snapshot-global-id", required=True)
@click.pass_context
def command(ctx: click.Context, snapshot_global_id: str) -> None:
    database_engine: Engine = ctx.obj["database"]["engine"]

    with Session(database_engine) as session, session.begin():
        stmt = (
            select(Snapshot)
            .where(Snapshot.global_id == snapshot_global_id)
            .with_for_update()
        )

        snapshot = session.scalar(stmt)
        if snapshot:

            with session.begin_nested():
                references = session.scalar(
                    select(func.count())
                    .select_from(Snapshot)
                    .where(Snapshot.source_id == snapshot.source_id)
                    .where(Snapshot.global_id != snapshot.global_id)
                )
                if references and references == 0:
                    if has_source_object(ctx, snapshot.source_id):
                        remove_source_object(ctx, snapshot.source_id)
            if has_database_object(ctx, snapshot.global_id):
                remove_database_object(ctx, snapshot.global_id)
            if has_sarif_object(ctx, snapshot.global_id):
                remove_sarif_object(ctx, snapshot.global_id)

            session.delete(snapshot)

        else:
            click.echo(f"No snapshot with id {snapshot_global_id}!")
