import click
from pathlib import Path
from typing import Optional
from subprocess import run
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from minio import Minio
from minio.error import S3Error
from models import Snapshot, SnapshotState
from helpers.hash import sha256_hexdigest
from helpers.zip import zipdir, ZipError
from tempfile import TemporaryDirectory


@click.command(name="add")
@click.option("--project-url")
@click.option("--branch")
@click.option("--commit")
@click.argument(
    "source-root",
    type=click.Path(exists=True, path_type=Path, file_okay=False),
    default=Path.cwd(),
)
@click.pass_context
def command(
    ctx: click.Context,
    project_url: Optional[str],
    branch: Optional[str],
    commit: Optional[str],
    source_root: Path,
):
    if project_url == None:
        project_url = resolve_project_url(source_root)
        if not project_url:
            raise click.exceptions.UsageError("Cannot resolve project url!")

    if branch == None:
        branch = resolve_branch(source_root)
        if not branch:
            raise click.exceptions.UsageError("Cannot resolve snapshot branch!")

    if commit == None:
        commit = resolve_commit(source_root)
        if not commit:
            raise click.exceptions.UsageError("Cannot resolve snapshot commit!")

    if not source_root.exists():
        raise click.exceptions.UsageError("Provided source root does not exist!")

    if not source_root.is_dir():
        raise click.exceptions.UsageError("Provided source root is not a directory!")

    database_engine: Engine = ctx.obj["database"]["engine"]

    with Session(database_engine) as session:
        stmt = (
            select(Snapshot)
            .where(Snapshot.project_url == project_url)
            .where(Snapshot.branch == branch)
            .where(Snapshot.commit == commit)
        )

        existing_snapshot = session.scalar(stmt)
        if existing_snapshot:
            if existing_snapshot.state == SnapshotState.BUILD_FAILED:
                click.echo(
                    f"Snapshot in state {existing_snapshot.state.name}. Resetting state to {SnapshotState.NOT_BUILT.name} to retry."
                )
                existing_snapshot.state = SnapshotState.NOT_BUILT
            elif existing_snapshot.state == SnapshotState.ANALYSIS_FAILED:
                if has_source_object(ctx, existing_snapshot):
                    click.echo(
                        f"Snapshot in state {existing_snapshot.state.name} and has a source object. Resetting state to {SnapshotState.NOT_ANALYZED.name} to retry."
                    )
                    existing_snapshot.state = SnapshotState.NOT_ANALYZED
                else:
                    click.echo(
                        f"Snapshot in state {existing_snapshot.state.name} and is missing a source object. Resetting state to {SnapshotState.NOT_BUILT.name}."
                    )
                    existing_snapshot.state = SnapshotState.NOT_BUILT
            elif existing_snapshot.state == SnapshotState.NOT_BUILT:
                if not has_source_object(ctx, existing_snapshot):
                    click.echo(
                        f"Snapshot exist in state {SnapshotState.NOT_BUILT.name}, but is missing a source object. Retrying to add source object."
                    )

                    try:
                        create_source_object(ctx, existing_snapshot, source_root)
                    except S3Error as err:
                        click.echo(
                            f"Failed to create source object! Adding snapshot with state {SnapshotState.SNAPSHOT_FAILED}"
                        )
                        existing_snapshot.state = SnapshotState.SNAPSHOT_FAILED
                    except ZipError as err:
                        click.echo(
                            f"Failed to create source archive! Adding snapshot with state {SnapshotState.SNAPSHOT_FAILED}"
                        )
                    existing_snapshot.state = SnapshotState.SNAPSHOT_FAILED
            elif existing_snapshot.state == SnapshotState.SNAPSHOT_FAILED:
                click.echo(
                    f"Snapshot exist in state {existing_snapshot.state.name}. Resetting to {SnapshotState.NOT_BUILT.name} to retry."
                )
                existing_snapshot.state = SnapshotState.NOT_BUILT
            else:
                click.echo(
                    f"Snapshot already exists in non-failed state {existing_snapshot.state.name}."
                )
        else:
            new_snapshot = Snapshot(
                project_url=project_url,
                branch=branch,
                commit=commit,
                state=SnapshotState.NOT_BUILT,
            )
            try:
                create_source_object(ctx, new_snapshot, source_root)
            except S3Error as err:
                click.echo(
                    f"Failed to create source object with error '{err}'! Adding snapshot with state {SnapshotState.SNAPSHOT_FAILED}"
                )
                new_snapshot.state = SnapshotState.SNAPSHOT_FAILED
            except ZipError as err:
                click.echo(
                    f"Failed to create source archive with error '{err}'! Adding snapshot with state {SnapshotState.SNAPSHOT_FAILED}"
                )
                new_snapshot.state = SnapshotState.SNAPSHOT_FAILED

            session.add(new_snapshot)
        session.commit()


def resolve_project_url(source_root: Path):
    git_dir = source_root / ".git"
    if git_dir.exists():
        completed_proc = run(
            ["git", f"--git-dir={str(git_dir)}", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
        )
        if completed_proc.returncode != 0:
            return None
        return completed_proc.stdout.strip()
    else:
        return None


def resolve_branch(source_root: Path):
    git_dir = source_root / ".git"
    if git_dir.exists():
        completed_proc = run(
            ["git", f"--git-dir={git_dir}", "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
        )
        if completed_proc.returncode != 0:
            return None
        return completed_proc.stdout.strip()
    else:
        return None


def resolve_commit(source_root: Path):
    git_dir = source_root / ".git"
    if git_dir.exists():
        completed_proc = run(
            ["git", f"--git-dir={git_dir}", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        )
        if completed_proc.returncode != 0:
            return None
        return completed_proc.stdout.strip()
    else:
        return None


def has_source_object(ctx: click.Context, snapshot: Snapshot) -> bool:
    snapshot_digest = sha256_hexdigest(
        f"{snapshot.project_url}-{snapshot.branch}-{snapshot.commit}"
    )
    try:
        ctx.obj["storage"]["client"].stat_object(
            ctx.obj["storage"]["buckets"]["source"], snapshot_digest
        )
        return True
    except S3Error as err:
        if err.code == "NoSuchKey":
            return False
        else:
            raise err


def create_source_object(ctx: click.Context, snapshot: Snapshot, source_root: Path):
    snapshot_digest = sha256_hexdigest(
        f"{snapshot.project_url}-{snapshot.branch}-{snapshot.commit}"
    )
    with TemporaryDirectory() as tmpdir:
        tmpzip = (Path(tmpdir) / snapshot_digest).with_suffix(".zip")
        zipdir(source_root, tmpzip)

        ctx.obj["storage"]["client"].fput_object(
            ctx.obj["storage"]["buckets"]["source"], snapshot_digest, str(tmpzip)
        )
