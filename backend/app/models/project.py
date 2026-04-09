import enum
from datetime import datetime, date

from sqlalchemy import String, Text, Enum, DateTime, Date, Integer, ForeignKey, JSON, Boolean, Numeric
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


class BudgetType(str, enum.Enum):
    amount = "金额"
    discount_rate = "折扣率"
    float_down_rate = "下浮率"


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


class ContractStatus(str, enum.Enum):
    none = "无"
    unsigned = "未签订"
    signed_not_returned = "已签订未收回"
    signed_returned = "已签订已收回"


class ResultDepositStatus(str, enum.Enum):
    not_returned = "未收回"
    returned = "已收回"


class ProjectInfo(Base):
    __tablename__ = "project_infos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ---- Section 1: 项目基本信息 (创建即有) ----
    bidding_type: Mapped[str] = mapped_column(Enum(BiddingType), nullable=False)
    project_name: Mapped[str] = mapped_column(String(300), nullable=False)
    bidding_unit_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=True)
    region: Mapped[str] = mapped_column(String(100), default="")
    manager_ids: Mapped[str] = mapped_column(JSON, default=[])
    status: Mapped[str] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.following)
    description: Mapped[str] = mapped_column(Text, default="")
    abandon_reason: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # ---- Section 2: 招标信息 (status >= 已发公告) ----
    agency_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=True)
    publish_platform_id: Mapped[int] = mapped_column(Integer, ForeignKey("platforms.id"), nullable=True)
    tags: Mapped[str] = mapped_column(JSON, default=[])
    registration_deadline: Mapped[date] = mapped_column(Date, nullable=True)
    bid_deadline: Mapped[date] = mapped_column(Date, nullable=True)
    budget_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    control_price_type: Mapped[str] = mapped_column(Enum(BudgetType), default=BudgetType.amount)
    control_price_upper: Mapped[float] = mapped_column(Numeric(15, 2), nullable=True)
    control_price_lower: Mapped[float] = mapped_column(Numeric(15, 2), nullable=True)
    is_prequalification: Mapped[bool] = mapped_column(Boolean, default=False)
    bid_specialist_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    bid_documents: Mapped[str] = mapped_column(JSON, default=[])
    bidding_notes: Mapped[str] = mapped_column(Text, default="")

    # ---- Section 3: 投标信息 (status >= 准备投标) ----
    partner_ids: Mapped[str] = mapped_column(JSON, default=[])
    bid_method: Mapped[str] = mapped_column(Enum(BidMethod), default=BidMethod.independent)
    bid_status: Mapped[str] = mapped_column(Enum(BidStatus), default=BidStatus.not_registered)
    has_deposit: Mapped[bool] = mapped_column(Boolean, default=False)
    deposit_status: Mapped[str] = mapped_column(Enum(DepositStatus), default=DepositStatus.none)
    deposit_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    deposit_date: Mapped[date] = mapped_column(Date, nullable=True)
    deposit_return_date: Mapped[date] = mapped_column(Date, nullable=True)
    bid_files: Mapped[str] = mapped_column(JSON, default=[])
    our_price: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    bid_notes: Mapped[str] = mapped_column(Text, default="")

    # ---- Section 4: 投标结果 (status >= 已投标) ----
    competitors: Mapped[str] = mapped_column(JSON, default=[])
    scoring_details: Mapped[str] = mapped_column(JSON, default=[])
    result_deposit_status: Mapped[str] = mapped_column(Enum(ResultDepositStatus), nullable=True)
    is_won: Mapped[bool] = mapped_column(Boolean, default=False)
    winning_org_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=True)
    winning_org_ids: Mapped[str] = mapped_column(JSON, default=[])
    winning_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=True)
    winning_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=True)
    lost_analysis: Mapped[str] = mapped_column(Text, default="")
    contract_number: Mapped[str] = mapped_column(String(100), default="")
    contract_status: Mapped[str] = mapped_column(Enum(ContractStatus), default=ContractStatus.none)
    contract_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    result_notes: Mapped[str] = mapped_column(Text, default="")
