import enum
from datetime import datetime

from sqlalchemy import String, Text, Enum, DateTime, Integer, ForeignKey, JSON, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class ContractStatus(str, enum.Enum):
    none = "无"
    unsigned = "未签订"
    signed_not_returned = "已签订未收回"
    signed_returned = "已签订已收回"


class ResultDepositStatus(str, enum.Enum):
    not_returned = "未收回"
    returned = "已收回"


class BidResult(Base):
    __tablename__ = "bid_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bid_info_id: Mapped[int] = mapped_column(Integer, ForeignKey("bid_infos.id"), unique=True, nullable=False)
    our_price: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    competitors: Mapped[str] = mapped_column(JSON, default=[])  # [{"org_id": 1, "price": 100000}]
    scoring_details: Mapped[str] = mapped_column(JSON, default=[])  # [{"org_id": 1, "score": 85.5}]
    deposit_status: Mapped[str] = mapped_column(Enum(ResultDepositStatus), nullable=True)
    is_won: Mapped[bool] = mapped_column(Boolean, default=False)
    lost_analysis: Mapped[str] = mapped_column(Text, default="")
    contract_number: Mapped[str] = mapped_column(String(100), default="")
    contract_status: Mapped[str] = mapped_column(Enum(ContractStatus), default=ContractStatus.none)
    contract_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
