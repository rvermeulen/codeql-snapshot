import subprocess
import json
import semantic_version
from pathlib import Path


class CodeQLException(Exception):
    pass


class CodeQL:
    def _exec(self, command: str, *args: str) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                ["codeql", command] + [arg for arg in args],
                capture_output=True,
                text=True,
            )
        except OSError as e:
            raise CodeQLException(
                f"Failed to execute codeql command with error: {e.strerror}!"
            )

    def version(self) -> semantic_version.Version:
        cp = self._exec("version", "--format=json")
        if cp.returncode == 0:
            version_info = json.loads(cp.stdout)
            return semantic_version.Version(version_info["version"])
        else:
            raise CodeQLException(f"Failed to run {cp.args} command!")

    def database_create(
        self,
        language: str,
        source_root: Path,
        database: Path,
        **kwargs: str,
    ) -> None:
        arguments = [
            "database",
            "create",
            f"--language={language}",
            f"--source-root={source_root}",
        ]

        for key, value in kwargs.items():
            arguments.append(f"--{key}={value}")

        cp = self._exec(
            *arguments,
            str(database),
        )
        if cp.returncode != 0:
            raise CodeQLException(f"Failed to run {cp.args} command!")

    def database_bundle(self, database: Path) -> Path:
        bundle_path = database.with_suffix(".zip")

        cp = self._exec(
            "database",
            "bundle",
            f"--output={bundle_path}",
            "--mode=brutal",
            str(database),
        )

        if cp.returncode != 0:
            raise CodeQLException(f"Failed to run {cp.args} command!")
        return bundle_path

    def database_unbundle(self, bundled_database: Path) -> None:
        unbundled_database_name = bundled_database.with_suffix("").stem
        cp = self._exec(
            "database",
            "unbundle",
            f"--name={unbundled_database_name}",
            f"--target={bundled_database.parent}",
            "--",
            str(bundled_database),
        )

        if cp.returncode != 0:
            raise CodeQLException(f"Failed to run {cp.args} command!")

    def database_analyze(self, database: Path, sarif: Path, **kwargs: str) -> None:
        cp = self._exec(
            "database",
            "analyze",
            "--format=sarifv2.1.0",
            f"--output={sarif}",
            "--sarif-add-file-contents",
            *[f"--{key}={value}" for key, value in kwargs.items()],
            str(database)
        )

        if cp.returncode != 0:
            print(cp.stderr)
            raise CodeQLException(f"Failed to run {cp.args} command!")
