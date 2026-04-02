import enum
from datetime import date, datetime

from sqlalchemy import String, Text, Enum, DateTime, Integer, ForeignKey, JSON, Boolean, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class BidMethod(str, enum.Enum):
    independent = "独立"
    consortium = "联合体"
    cooperate = "配合"
    companion = "陪标"


class BidStatus(str, enum.Enum):
    no_bid = "不投标"
    not_registered = "未报名"
    registered = "已报名"
    submitted = "已投标"


class DepositStatus(str, enum.Enum):
    none = "无"
    unpaid = "未缴纳"
    paid = "已缴纳"
    not_returned = "未收回"
    returned = "已收回"


class BidInfo(Base):
    __tablename__ = "bid_infos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bidding_info_id: Mapped[int] = mapped_column(Integer, ForeignKey("bidding_infos.id"), unique=True, nullable=False)
    partner_ids: Mapped[str] = mapped_column(JSON, default=[])  # Organization IDs
    bid_method: Mapped[str] = mapped_column(Enum(BidMethod), default=BidMethod.independent)
    bid_status: Mapped[str] = mapped_column(Enum(BidStatus), default=BidStatus.not_registered)
    has_deposit: Mapped[bool] = mapped_column(Boolean, default=False)
    deposit_status: Mapped[str] = mapped_column(Enum(DepositStatus), default=DepositStatus.none)
    deposit_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    deposit_date: Mapped[date] = mapped_column(Date, nullable=True)
    deposit_return_date: Mapped[date] = mapped_column(Date, nullable=True)
    bid_files: Mapped[str] = mapped_column(JSON, default=[])  # file paths
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
