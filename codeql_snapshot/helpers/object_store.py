import click
from models import Snapshot
from pathlib import Path
from minio import Minio
from minio.error import S3Error
from helpers.zip import zipdir
from tempfile import TemporaryDirectory


def has_source_object(ctx: click.Context, snapshot: Snapshot) -> bool:
    try:
        ctx.obj["storage"]["client"].stat_object(
            ctx.obj["storage"]["buckets"]["source"], snapshot.source_id
        )
        return True
    except S3Error as err:
        if err.code == "NoSuchKey":
            return False
        else:
            raise err


def create_source_object(
    ctx: click.Context, snapshot: Snapshot, source_root: Path
) -> None:
    with TemporaryDirectory() as tmpdir:
        tmpzip = (Path(tmpdir) / snapshot.global_id).with_suffix(".zip")
        zipdir(source_root, tmpzip)

        ctx.obj["storage"]["client"].fput_object(
            ctx.obj["storage"]["buckets"]["source"], snapshot.source_id, str(tmpzip)
        )


def get_source_object(
    ctx: click.Context, snapshot: Snapshot, object_file: Path
) -> None:
    client: Minio = ctx.obj["storage"]["client"]
    source_bucket: str = ctx.obj["storage"]["buckets"]["source"]
    client.fget_object(source_bucket, snapshot.source_id, str(object_file))


def create_database_object(
    ctx: click.Context, snapshot: Snapshot, database_bundle: Path
) -> None:
    ctx.obj["storage"]["client"].fput_object(
        ctx.obj["storage"]["buckets"]["database"],
        snapshot.global_id,
        str(database_bundle),
    )
