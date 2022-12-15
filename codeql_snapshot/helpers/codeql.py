import subprocess
import json
import semantic_version
from pathlib import Path
from typing import Tuple


class CodeQLException(Exception):
    pass


class CodeQL:
    def _exec(self, command: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["codeql", command] + [arg for arg in args], capture_output=True, text=True
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
        **kwargs: Tuple[str, str],
    ):
        cp = self._exec(
            "database",
            "create",
            f"--language={language}",
            f"--source-root={source_root}",
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
