from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, Any


class BidInfoCreate(BaseModel):
    bidding_info_id: int
    partner_ids: list[int] = []
    bid_method: str = "独立"
    bid_status: str = "未报名"
    has_deposit: bool = False
    deposit_status: str = "无"
    deposit_amount: float = 0
    deposit_date: Optional[date] = None
    deposit_return_date: Optional[date] = None
    bid_files: list[str] = []
    notes: str = ""


class BidInfoUpdate(BaseModel):
    partner_ids: Optional[list[int]] = None
    bid_method: Optional[str] = None
    bid_status: Optional[str] = None
    has_deposit: Optional[bool] = None
    deposit_status: Optional[str] = None
    deposit_amount: Optional[float] = None
    deposit_date: Optional[date] = None
    deposit_return_date: Optional[date] = None
    bid_files: Optional[list[str]] = None
    notes: Optional[str] = None


class BidInfoResponse(BaseModel):
    id: int
    bidding_info_id: int
    partner_ids: Any
    bid_method: str
    bid_status: str
    has_deposit: bool
    deposit_status: str
    deposit_amount: float
    deposit_date: Optional[date]
    deposit_return_date: Optional[date]
    bid_files: Any
    notes: str
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    # Enriched
    project_name: Optional[str] = None
    partner_names: Optional[list[str]] = None
    model_config = {"from_attributes": True}
