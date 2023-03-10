import click
from sqlalchemy import create_engine
from minio import Minio
from typing import Optional, List, Any, Type
from models import Base
from pathlib import Path

commands_directory: Path = Path(__file__).parent / "commands"


class LazyMultiCommand(click.MultiCommand):
    def list_commands(self, ctx: click.Context) -> List[str]:
        return sorted(
            [
                command.with_suffix("").name
                for command in commands_directory.iterdir()
                if command.suffix == ".py" and not command.name == "__init__.py"
            ]
        )

    def get_command(self, ctx: click.Context, cmd_name: str) -> Optional[click.Command]:
        namespace: dict[str, Any] = {}
        command_module_path = (commands_directory / cmd_name).with_suffix(".py")
        with command_module_path.open(mode="r") as fd:
            code = compile(fd.read(), command_module_path, "exec")
            eval(code, namespace, namespace)
        command: Optional[click.Command] = namespace["command"]
        return command


@click.command(cls=LazyMultiCommand)
@click.option(
    "--connection-string",
    required=True,
    help="Connection string to connect to SQL database server used to store state.",
)
@click.option(
    "--storage-host",
    required=True,
    help="Host of a S3 compatible object storage to store artifacts.",
)
@click.option(
    "--storage-access-key",
    required=True,
    help="Access key used to access S3 compatible object store.",
)
@click.option(
    "--storage-secret-key",
    required=True,
    help="Access key used to access S3 compatible object store.",
)
@click.option("--storage-source-bucket", default="sources")
@click.option("--storage-database-bucket", default="databases")
@click.option("--storage-sarif-bucket", default="sarifs")
@click.pass_context
def cli(
    ctx: click.Context,
    connection_string: str,
    storage_host: str,
    storage_access_key: str,
    storage_secret_key: str,
    storage_source_bucket: str,
    storage_database_bucket: str,
    storage_sarif_bucket: str,
):
    ctx.ensure_object(dict)

    ctx.obj["database"] = {"engine": create_engine(connection_string, echo=False)}
    storage_client = Minio(
        storage_host,
        access_key=storage_access_key,
        secret_key=storage_secret_key,
        secure=False,
    )
    ctx.obj["storage"] = {
        "client": storage_client,
        "buckets": {
            "source": storage_source_bucket,
            "database": storage_database_bucket,
            "sarif": storage_sarif_bucket,
        },
    }
    # Initialize database
    Base.metadata.create_all(ctx.obj["database"]["engine"])
    # Initialize buckets
    if not storage_client.bucket_exists(storage_source_bucket):
        storage_client.make_bucket(storage_source_bucket)
    if not storage_client.bucket_exists(storage_database_bucket):
        storage_client.make_bucket(storage_database_bucket)
    if not storage_client.bucket_exists(storage_sarif_bucket):
        storage_client.make_bucket(storage_sarif_bucket)


if __name__ == "__main__":
    cli(obj={}, auto_envvar_prefix="CODEQL_SNAPSHOT")
