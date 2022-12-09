from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base
from enum import Enum


class SnapshotState(Enum):
    SNAPSHOT_FAILED = "SNAPSHOT_FAILED"
    NOT_BUILT = "NOT_BUILT"
    BUILD_IN_PROGRESS = "BUILD_IN_PROGRESS"
    BUILD_FAILED = "BUILD_FAILED"
    NOT_ANALYZED = "NOT_ANALYZED"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    ANALYSIS_IN_PROGRESS = "ANALYSIS_IN_PROGRESS"
    ANALYZED = "ANALYZED"


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    # https://support.microsoft.com/en-us/topic/maximum-url-length-is-2-083-characters-in-internet-explorer-174e7c8a-6666-f4e0-6fd6-908b53c12246
    project_url: Mapped[str] = mapped_column(String(2048))
    branch: Mapped[str] = mapped_column(String(255))
    commit: Mapped[str] = mapped_column(String(40))
    state: Mapped[SnapshotState]
