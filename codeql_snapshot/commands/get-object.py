import click
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from codeql_snapshot.helpers.object_store import (
    has_database_object,
    get_database_object,
    has_sarif_object,
    get_sarif_object,
)
from codeql_snapshot.models.snapshot import Snapshot
from pathlib import Path


@click.command(name="get-object")
@click.option("-s", "--snapshot-global-id", required=True)
@click.option(
    "-t",
    "--object-type",
    required=True,
    type=click.Choice(
        ["database", "sarif"],
        case_sensitive=False,
    ),
)
@click.argument(
    "directory", type=click.Path(exists=True, path_type=Path, file_okay=False)
)
@click.pass_context
def command(
    ctx: click.Context, snapshot_global_id: str, object_type: str, directory: Path
) -> None:
    database_engine: Engine = ctx.obj["database"]["engine"]

    with Session(database_engine) as session:
        stmt = select(Snapshot).where(Snapshot.global_id == snapshot_global_id)

        snapshot = session.scalar(stmt)
        if snapshot:

            if object_type == "database":
                if has_database_object(ctx, snapshot.global_id):
                    database_path = (directory / snapshot.global_id).with_suffix(".zip")
                    if database_path.exists():
                        click.echo(f"Database already exists at {database_path}!")
                        return
                    get_database_object(
                        ctx,
                        snapshot.global_id,
                        database_path,
                    )
                else:
                    click.echo(
                        f"No database for snapshot with id {snapshot_global_id}!"
                    )

            if object_type == "sarif":
                sarif_path = (directory / snapshot.global_id).with_suffix(".sarif")
                if sarif_path.exists():
                    click.echo(f"Sarif already exists at {sarif_path}!")
                    return
                if has_sarif_object(ctx, snapshot.global_id):
                    get_sarif_object(
                        ctx,
                        snapshot.global_id,
                        sarif_path,
                    )
                else:
                    click.echo(f"No sarif for snapshot with id {snapshot_global_id}!")
        else:
            click.echo(f"No snapshot with id {snapshot_global_id}!")
