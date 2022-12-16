import click
from models import Snapshot
from pathlib import Path
from minio import Minio
from minio.error import S3Error
from helpers.zip import zipdir
from tempfile import TemporaryDirectory


def _has_object(client: Minio, bucket: str, key: str) -> bool:
    try:
        client.stat_object(bucket, key)
        return True
    except S3Error as err:
        if err.code == "NoSuchKey":
            return False
        else:
            raise err


def _get_object(client: Minio, bucket: str, key: str, object_file: Path) -> None:
    client.fget_object(bucket, key, str(object_file))


def _create_object(client: Minio, bucket: str, key: str, object_file: Path) -> None:
    client.fput_object(bucket, key, str(object_file))


def has_source_object(ctx: click.Context, snapshot: Snapshot) -> bool:
    return _has_object(
        ctx.obj["storage"]["client"],
        ctx.obj["storage"]["buckets"]["source"],
        snapshot.source_id,
    )


def create_source_object(
    ctx: click.Context, snapshot: Snapshot, source_root: Path
) -> None:
    with TemporaryDirectory() as tmpdir:
        tmpzip = (Path(tmpdir) / snapshot.global_id).with_suffix(".zip")
        zipdir(source_root, tmpzip)

        _create_object(
            ctx.obj["storage"]["client"],
            ctx.obj["storage"]["buckets"]["source"],
            snapshot.source_id,
            tmpzip,
        )


def get_source_object(
    ctx: click.Context, snapshot: Snapshot, object_file: Path
) -> None:
    _get_object(
        ctx.obj["storage"]["client"],
        ctx.obj["storage"]["buckets"]["source"],
        snapshot.source_id,
        object_file,
    )


def has_database_object(ctx: click.Context, snapshot: Snapshot) -> bool:
    return _has_object(
        ctx.obj["storage"]["client"],
        ctx.obj["storage"]["buckets"]["database"],
        snapshot.global_id,
    )


def create_database_object(
    ctx: click.Context, snapshot: Snapshot, database_bundle: Path
) -> None:
    _create_object(
        ctx.obj["storage"]["client"],
        ctx.obj["storage"]["buckets"]["database"],
        snapshot.global_id,
        database_bundle,
    )


def get_database_object(
    ctx: click.Context, snapshot: Snapshot, object_file: Path
) -> None:
    _get_object(
        ctx.obj["storage"]["client"],
        ctx.obj["storage"]["buckets"]["database"],
        snapshot.global_id,
        object_file,
    )


def has_sarif_object(ctx: click.Context, snapshot: Snapshot) -> bool:
    return _has_object(
        ctx.obj["storage"]["client"],
        ctx.obj["storage"]["buckets"]["sarif"],
        snapshot.global_id,
    )


def create_sarif_object(ctx: click.Context, snapshot: Snapshot, sarif: Path) -> None:
    _create_object(
        ctx.obj["storage"]["client"],
        ctx.obj["storage"]["buckets"]["sarif"],
        snapshot.global_id,
        sarif,
    )


def get_sarif_object(ctx: click.Context, snapshot: Snapshot, object_file: Path) -> None:
    _get_object(
        ctx.obj["storage"]["client"],
        ctx.obj["storage"]["buckets"]["sarif"],
        snapshot.global_id,
        object_file,
    )
