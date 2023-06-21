import click
from alembic.config import Config
from alembic.command import upgrade


@click.command(name="init")
@click.pass_context
def command(
    ctx: click.Context,
):
    alembic_config_path = (ctx.obj['root_directory'] / "alembic.ini").absolute()
    if not alembic_config_path.exists():
        raise click.ClickException(f"Cannot find Alembic config file at {alembic_config_path}!")
    
    alembic_config = Config(alembic_config_path)
    # Initialize database
    upgrade(alembic_config, "head")

    storage_client = ctx.obj["storage"]["client"]
    # Initialize buckets
    if not storage_client.bucket_exists(ctx.obj["storage"]["buckets"]["source"]):
        storage_client.make_bucket(ctx.obj["storage"]["buckets"]["source"])
    if not storage_client.bucket_exists(ctx.obj["storage"]["buckets"]["database"]):
        storage_client.make_bucket(ctx.obj["storage"]["buckets"]["database"])
    if not storage_client.bucket_exists(ctx.obj["storage"]["buckets"]["sarif"]):
        storage_client.make_bucket(ctx.obj["storage"]["buckets"]["sarif"])
