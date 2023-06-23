from sqlalchemy import String, Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, validates
from sqlalchemy.engine.default import DefaultExecutionContext
from codeql_snapshot.models import Base
from enum import Enum
from typing import Any
from codeql_snapshot.helpers.hash import sha256_hexdigest


class SnapshotState(Enum):
    SNAPSHOT_FAILED = "SNAPSHOT_FAILED"
    NOT_BUILT = "NOT_BUILT"
    BUILD_IN_PROGRESS = "BUILD_IN_PROGRESS"
    BUILD_FAILED = "BUILD_FAILED"
    NOT_ANALYZED = "NOT_ANALYZED"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    ANALYSIS_IN_PROGRESS = "ANALYSIS_IN_PROGRESS"
    ANALYZED = "ANALYZED"


class SnapshotLanguage(Enum):
    JAVA = "java"
    CPP = "cpp"
    JAVASCRIPT = "javascript"
    PYTHON = "python"
    RUBY = "ruby"
    SWIFT = "swift"
    GO = "go"
    CSHARP = "csharp"

def get_global_id(context: DefaultExecutionContext) -> str:
    project_url = context.get_current_parameters()["project_url"]
    branch = context.get_current_parameters()["branch"]
    commit = context.get_current_parameters()["commit"]
    language = context.get_current_parameters()["language"]
    return sha256_hexdigest(f"{project_url}-{branch}-{commit}-{language}")


def get_source_id(context: DefaultExecutionContext) -> str:
    project_url = context.get_current_parameters()["project_url"]
    branch = context.get_current_parameters()["branch"]
    commit = context.get_current_parameters()["commit"]
    return sha256_hexdigest(f"{project_url}-{branch}-{commit}")

class Snapshot(Base):
    __tablename__ = "snapshots"

    global_id: Mapped[str] = mapped_column(String(64), default=get_global_id, init=False, unique=True)
    source_id: Mapped[str] = mapped_column(String(64), default=get_source_id, init=False)
    # https://support.microsoft.com/en-us/topic/maximum-url-length-is-2-083-characters-in-internet-explorer-174e7c8a-6666-f4e0-6fd6-908b53c12246
    project_url: Mapped[str] = mapped_column(String(2048), primary_key=True)
    branch: Mapped[str] = mapped_column(String(255), primary_key=True)
    commit: Mapped[str] = mapped_column(String(40), primary_key=True)
    language: Mapped[SnapshotLanguage] = mapped_column(
        SqlEnum(SnapshotLanguage), primary_key=True
    )
    label: Mapped[str] = mapped_column(String(255), default="default")
    state: Mapped[SnapshotState] = mapped_column(
        SqlEnum(SnapshotState), default=SnapshotState.NOT_BUILT
    )

    @validates("global_id", "source_id", "project_url", "branch", "commit", "language")
    def ensure_write_once(self, key: str, value: Any) -> Any:
        existing = getattr(self, key)
        if existing:
            raise ValueError(f"The field {key} should not be updated!")
        return value
