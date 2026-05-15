from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, Any


class ProjectCreate(BaseModel):
    """创建项目 — 仅项目基本信息字段"""
    bidding_type: str
    project_name: str
    bidding_unit_id: Optional[int] = None
    region: str = ""
    manager_ids: list[int] = []
    description: str = ""
    parent_project_id: Optional[int] = None
    is_multi_lot: Optional[bool] = False


class ProjectUpdate(BaseModel):
    """更新项目 — 所有字段 Optional，前端只发变化的字段"""
    # Section 1: 项目基本信息
    bidding_type: Optional[str] = None
    project_name: Optional[str] = None
    bidding_unit_id: Optional[int] = None
    region: Optional[str] = None
    manager_ids: Optional[list[int]] = None
    description: Optional[str] = None
    abandon_reason: Optional[str] = None
    parent_project_id: Optional[int] = None
    # Section 2: 招标信息
    agency_id: Optional[int] = None
    publish_platform_id: Optional[int] = None
    tags: Optional[list[str]] = None
    registration_deadline: Optional[date] = None
    bid_deadline: Optional[date] = None
    budget_amount: Optional[float] = None
    control_price_type: Optional[str] = None
    control_price_upper: Optional[float] = None
    control_price_lower: Optional[float] = None
    is_prequalification: Optional[bool] = None
    is_multi_lot: Optional[bool] = None
    bid_specialist_id: Optional[int] = None
    bid_documents: Optional[list[str]] = None
    bidding_notes: Optional[str] = None
    # Section 3: 投标信息
    partner_ids: Optional[list[int]] = None
    bid_method: Optional[str] = None
    is_consortium_lead: Optional[bool] = None
    bid_status: Optional[str] = None
    has_deposit: Optional[bool] = None
    deposit_status: Optional[str] = None
    deposit_amount: Optional[float] = None
    deposit_date: Optional[date] = None
    deposit_return_date: Optional[date] = None
    bid_files: Optional[list[str]] = None
    our_price: Optional[float] = None
    bid_notes: Optional[str] = None
    # Section 4: 投标结果
    competitors: Optional[list[dict]] = None
    scoring_details: Optional[list[dict]] = None
    result_deposit_status: Optional[str] = None
    is_won: Optional[bool] = None
    is_bid_failed: Optional[bool] = None
    is_registered: Optional[bool] = None  # 虚拟字段，不存DB
    winning_org_id: Optional[int] = None
    winning_org_ids: Optional[list[int]] = None
    winning_price: Optional[float] = None
    winning_amount: Optional[float] = None
    lost_analysis: Optional[str] = None
    contract_number: Optional[str] = None
    contract_status: Optional[str] = None
    contract_amount: Optional[float] = None
    result_notes: Optional[str] = None


class ProjectResponse(BaseModel):
    """项目响应 — 所有字段 + enrich 字段"""
    id: int
    # Section 1
    bidding_type: str
    project_name: str
    bidding_unit_id: Optional[int]
    region: str
    manager_ids: Any
    status: str
    description: str
    abandon_reason: str
    parent_project_id: Optional[int] = None
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    # Section 2
    agency_id: Optional[int] = None
    publish_platform_id: Optional[int] = None
    tags: Any = []
    registration_deadline: Optional[date] = None
    bid_deadline: Optional[date] = None
    budget_amount: float = 0
    control_price_type: Optional[str] = None
    control_price_upper: Optional[float] = None
    control_price_lower: Optional[float] = None
    is_prequalification: bool = False
    is_multi_lot: bool = False
    bid_specialist_id: Optional[int] = None
    bid_documents: Any = []
    bidding_notes: str = ""
    # Section 3
    partner_ids: Any = []
    bid_method: Optional[str] = None
    is_consortium_lead: bool = True
    bid_status: Optional[str] = None
    has_deposit: bool = False
    deposit_status: Optional[str] = None
    deposit_amount: float = 0
    deposit_date: Optional[date] = None
    deposit_return_date: Optional[date] = None
    bid_files: Any = []
    our_price: float = 0
    bid_notes: str = ""
    # Section 4
    competitors: Any = []
    scoring_details: Any = []
    result_deposit_status: Optional[str] = None
    is_won: bool = False
    is_bid_failed: bool = False
    is_registered: bool = False  # 虚拟字段，从 status 推导
    winning_org_id: Optional[int] = None
    winning_org_ids: Any = []
    winning_price: Optional[float] = None
    winning_amount: Optional[float] = None
    lost_analysis: str = ""
    contract_number: str = ""
    contract_status: Optional[str] = None
    contract_amount: float = 0
    result_notes: str = ""
    # Enriched fields
    parent_project_name: Optional[str] = None
    parent_is_multi_lot: Optional[bool] = None
    bidding_unit_name: Optional[str] = None
    manager_names: Optional[list[str]] = None
    agency_name: Optional[str] = None
    platform_name: Optional[str] = None
    specialist_name: Optional[str] = None
    partner_names: Optional[list[str]] = None
    winning_org_name: Optional[str] = None
    winning_org_names: Optional[list[str]] = None
    our_price_display: Optional[str] = None
    winning_price_display: Optional[str] = None
    winning_amount_display: Optional[str] = None
    deposit_status_display: Optional[str] = None
    model_config = {"from_attributes": True}
