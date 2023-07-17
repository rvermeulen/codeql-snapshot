import click
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from codeql_snapshot.models import Snapshot
from beautifultable import BeautifulTable
from shutil import get_terminal_size
from typing import Dict, Any
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
            table.columns.header = "Global Id, Source Id, Project Url,Branch,Commit,Language,Category,State,Labels,Created At,Updated At".split(
                ","
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
                        snapshot.category,
                        snapshot.state.name,
                        snapshot.label,
                        snapshot.created_at.replace(microsecond=0).isoformat(),
                        snapshot.updated_at.replace(microsecond=0).isoformat(),
                    ]
                )
            click.echo(table)
        elif format == "json":

            def snapshot_to_dict(snapshot: Snapshot) -> Dict[str, Any]:
                return {
                    "global-id": snapshot.global_id,
                    "source-id": snapshot.source_id,
                    "project-url": snapshot.project_url,
                    "branch": snapshot.branch,
                    "commit": snapshot.commit,
                    "language": snapshot.language.name,
                    "category": snapshot.category,
                    "state": snapshot.state.name,
                    "label": snapshot.label,
                    "created-at": snapshot.created_at.replace(
                        microsecond=0
                    ).isoformat(),
                    "updated-at": snapshot.updated_at.replace(
                        microsecond=0
                    ).isoformat(),
                }

            click.echo(json.dumps(list(map(snapshot_to_dict, snapshots)), indent=2))

        else:
            raise click.BadOptionUsage(
                option_name="--format",
                message=f"Unimplemented format {format} specified!",
            )
