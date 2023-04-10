import zipfile
from pathlib import Path
import click


class ZipError(Exception):
    pass


def zipdir(source_dir: Path, zip_path: Path):
    if not source_dir.is_dir():
        raise ZipError(f"The provided source path {source_dir} is not a directory!")

    if zip_path.exists():
        raise ZipError(f"The provided zip path already exists!")

    if zip_path.suffix != ".zip":
        raise ZipError(f"The provided zip path doesn't end with '.zip'")

    with zipfile.ZipFile(str(zip_path), mode="x") as fd:
        with click.progressbar([p for p in source_dir.glob("**/*")]) as files:
            for f in files:
                try:
                    fd.write(str(f), arcname=str(f.relative_to(source_dir)))
                except ValueError as e:
                    raise ZipError(f"Failed to zip file {f} with error {e}")
