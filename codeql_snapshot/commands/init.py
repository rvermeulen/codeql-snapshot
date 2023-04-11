import click
from codeql_snapshot.models import Base


@click.command(name="init")
@click.pass_context
def command(
    ctx: click.Context,
):

    # Initialize database
    Base.metadata.create_all(ctx.obj["database"]["engine"])

    storage_client = ctx.obj["storage"]["client"]
    # Initialize buckets
    if not storage_client.bucket_exists(ctx.obj["storage"]["buckets"]["source"]):
        storage_client.make_bucket(ctx.obj["storage"]["buckets"]["source"])
    if not storage_client.bucket_exists(ctx.obj["storage"]["buckets"]["database"]):
        storage_client.make_bucket(ctx.obj["storage"]["buckets"]["database"])
    if not storage_client.bucket_exists(ctx.obj["storage"]["buckets"]["sarif"]):
        storage_client.make_bucket(ctx.obj["storage"]["buckets"]["sarif"])
