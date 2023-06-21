import click
from sqlalchemy import create_engine, text
from minio import Minio
from typing import Optional, List, Any
from pathlib import Path
from alembic import config, script
from alembic.runtime import migration

# Add the parent directory to the path if this module is run directly (i.e. not imported)
# This is necessary to support both the Poetry script invocation and the direct invocation.
if not __package__ and __name__ == "__main__":
    import sys

    sys.path.append(str(Path(__file__).parent.parent))
    __package__ = Path(__file__).parent.name

root_directory: Path = Path(__file__).parent
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
def multicommand(
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

    if ctx.invoked_subcommand != "init":
        alembic_config_path = (root_directory / "alembic.ini").absolute()
        if not alembic_config_path.exists():
            raise click.ClickException(
                f"Cannot find Alembic config file at {alembic_config_path}!"
            )
        alembic_config = config.Config(alembic_config_path)
        alembic_script_dir = script.ScriptDirectory.from_config(alembic_config)
        # Check if database is initialized
        with ctx.obj["database"]["engine"].connect() as connection:
            context = migration.MigrationContext.configure(connection)
            if set(context.get_current_heads()) != set(alembic_script_dir.get_heads()):
                    click.echo(
                        "Database schema is not up-to-date. Run `codeql-snapshot init` first."
                    )
                    exit(1)

        # Initialize buckets
        if (
            not storage_client.bucket_exists(storage_source_bucket)
            or not storage_client.bucket_exists(storage_database_bucket)
            or not storage_client.bucket_exists(storage_sarif_bucket)
        ):
            click.echo(
                "Object store not initialized. Run `codeql-snapshot init` first."
            )
            exit(1)


def main() -> None:
    multicommand(obj={"root_directory": root_directory}, auto_envvar_prefix="CODEQL_SNAPSHOT")

if __name__ == "__main__":
    main()
