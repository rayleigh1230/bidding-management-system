from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    triggered_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    sites_summary: Mapped[str] = mapped_column(JSON, default={})
    error_summary: Mapped[str] = mapped_column(JSON, default={})


class ScrapeItemLog(Base):
    __tablename__ = "scrape_item_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scrape_runs.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), default="")
    external_no: Mapped[str] = mapped_column(String(100), nullable=True)
    project_name: Mapped[str] = mapped_column(String(300), default="")
    source_url: Mapped[str] = mapped_column(String(500), nullable=True)
    result: Mapped[str] = mapped_column(String(20), default="")
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project_infos.id"), nullable=True
    )
    skip_reason: Mapped[str] = mapped_column(String(200), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
