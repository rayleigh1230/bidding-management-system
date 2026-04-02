import enum
from datetime import date, datetime

from sqlalchemy import String, Text, Enum, DateTime, Integer, ForeignKey, JSON, Boolean, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class BudgetType(str, enum.Enum):
    unit_price = "单价"
    total = "总金额"


class BiddingInfo(Base):
    __tablename__ = "bidding_infos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project_infos.id"), unique=True, nullable=False)
    agency_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=True)
    publish_platform_id: Mapped[int] = mapped_column(Integer, ForeignKey("platforms.id"), nullable=True)
    tags: Mapped[str] = mapped_column(JSON, default=[])  # ["信息化", "安防"]
    registration_deadline: Mapped[date] = mapped_column(Date, nullable=True)
    bid_deadline: Mapped[date] = mapped_column(Date, nullable=True)
    budget_type: Mapped[str] = mapped_column(Enum(BudgetType), default=BudgetType.total)
    budget_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    is_prequalification: Mapped[bool] = mapped_column(Boolean, default=False)
    bid_specialist_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    bid_documents: Mapped[str] = mapped_column(JSON, default=[])  # file paths
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
