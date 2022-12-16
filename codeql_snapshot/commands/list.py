import click
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from models import Snapshot, SnapshotState
from beautifultable import BeautifulTable
from shutil import get_terminal_size
from typing import Dict
import json


@click.command(name="list")
@click.option("--format", default="table", type=click.Choice(["table", "json"]))
@click.pass_context
def command(ctx: click.Context, format: str):
    database_engine: Engine = ctx.obj["database"]["engine"]
    with Session(database_engine) as session:
        select_snapshots = select(Snapshot)
        snapshots = session.scalars(select_snapshots)

        if format == "table":
            table = BeautifulTable(maxwidth=get_terminal_size()[0])
            table.columns.header = (
                "Global Id, Source Id, Project Url,Branch,Commit,Language,State".split(
                    ","
                )
            )
            table.columns.alignment = BeautifulTable.ALIGN_LEFT
            for snapshot in snapshots:
                table.append_row(
                    [
                        snapshot.global_id,
                        snapshot.source_id,
                        snapshot.project_url,
                        snapshot.branch,
                        snapshot.commit,
                        snapshot.language.name,
                        snapshot.state.name,
                    ]
                )
            click.echo(table)
        elif format == "json":

            def snapshot_to_dict(snapshot: Snapshot) -> Dict[str, str]:
                return {
                    "global-id": snapshot.global_id,
                    "source-id": snapshot.source_id,
                    "project-url": snapshot.project_url,
                    "branch": snapshot.branch,
                    "commit": snapshot.commit,
                    "language": snapshot.language.name,
                    "state": snapshot.state.name,
                }

            click.echo(json.dumps(list(map(snapshot_to_dict, snapshots)), indent=2))

        else:
            raise click.BadOptionUsage(
                option_name="--format",
                message=f"Unimplemented format {format} specified!",
            )
