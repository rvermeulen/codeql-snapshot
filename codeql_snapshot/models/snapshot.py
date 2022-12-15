from sqlalchemy import String, Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, validates
from sqlalchemy.engine.default import DefaultExecutionContext
from models.base import Base
from enum import Enum
from typing import Any
from helpers.hash import sha256_hexdigest


class SnapshotState(Enum):
    SNAPSHOT_FAILED = "SNAPSHOT_FAILED"
    NOT_BUILT = "NOT_BUILT"
    BUILD_IN_PROGRESS = "BUILD_IN_PROGRESS"
    BUILD_FAILED = "BUILD_FAILED"
    NOT_ANALYZED = "NOT_ANALYZED"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    ANALYSIS_IN_PROGRESS = "ANALYSIS_IN_PROGRESS"
    ANALYZED = "ANALYZED"


class SnaphotLanguage(Enum):
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


class Snapshot(Base):
    __tablename__ = "snapshots"

    global_id: Mapped[str] = mapped_column(default=get_global_id, init=False)
    # https://support.microsoft.com/en-us/topic/maximum-url-length-is-2-083-characters-in-internet-explorer-174e7c8a-6666-f4e0-6fd6-908b53c12246
    project_url: Mapped[str] = mapped_column(String(2048), primary_key=True)
    branch: Mapped[str] = mapped_column(String(255), primary_key=True)
    commit: Mapped[str] = mapped_column(String(40), primary_key=True)
    language: Mapped[SnaphotLanguage] = mapped_column(
        SqlEnum(SnaphotLanguage), primary_key=True
    )
    state: Mapped[SnapshotState] = mapped_column(
        SqlEnum(SnapshotState), default=SnapshotState.NOT_BUILT
    )

    @validates("project_url", "branch", "commit", "language")
    def ensure_read_only(self, key: str, value: Any) -> Any:
        existing = getattr(self, key)
        if existing:
            raise ValueError(f"The field {key} should not be updated!")
        return value
