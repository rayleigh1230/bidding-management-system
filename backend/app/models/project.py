import enum
from datetime import datetime

from sqlalchemy import String, Text, Enum, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class BiddingType(str, enum.Enum):
    public = "公开招标"
    invited = "邀请招标"
    intermediary = "中介超市"
    prequalification = "入围分项"


class ProjectStatus(str, enum.Enum):
    following = "跟进中"
    published = "已发公告"
    preparing = "准备投标"
    submitted = "已投标"
    won = "已中标"
    lost = "未中标"
    abandoned = "已放弃"


class ProjectInfo(Base):
    __tablename__ = "project_infos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bidding_type: Mapped[str] = mapped_column(Enum(BiddingType), nullable=False)
    project_name: Mapped[str] = mapped_column(String(300), nullable=False)
    bidding_unit_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=True)
    region: Mapped[str] = mapped_column(String(100), default="")  # JSON array [province, city, district]
    manager_ids: Mapped[str] = mapped_column(JSON, default=[])  # JSON array of manager IDs
    status: Mapped[str] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.following)
    description: Mapped[str] = mapped_column(Text, default="")
    abandon_reason: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
