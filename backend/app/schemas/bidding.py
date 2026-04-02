from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, Any


class BiddingInfoCreate(BaseModel):
    project_id: int
    agency_id: Optional[int] = None
    publish_platform_id: Optional[int] = None
    tags: list[str] = []
    registration_deadline: Optional[date] = None
    bid_deadline: Optional[date] = None
    budget_type: str = "总金额"
    budget_amount: float = 0
    is_prequalification: bool = False
    bid_specialist_id: Optional[int] = None
    bid_documents: list[str] = []
    notes: str = ""


class BiddingInfoUpdate(BaseModel):
    agency_id: Optional[int] = None
    publish_platform_id: Optional[int] = None
    tags: Optional[list[str]] = None
    registration_deadline: Optional[date] = None
    bid_deadline: Optional[date] = None
    budget_type: Optional[str] = None
    budget_amount: Optional[float] = None
    is_prequalification: Optional[bool] = None
    bid_specialist_id: Optional[int] = None
    bid_documents: Optional[list[str]] = None
    notes: Optional[str] = None


class BiddingInfoResponse(BaseModel):
    id: int
    project_id: int
    agency_id: Optional[int]
    publish_platform_id: Optional[int]
    tags: Any
    registration_deadline: Optional[date]
    bid_deadline: Optional[date]
    budget_type: str
    budget_amount: float
    is_prequalification: bool
    bid_specialist_id: Optional[int]
    bid_documents: Any
    notes: str
    created_at: datetime
    updated_at: datetime
    # Enriched fields
    project_name: Optional[str] = None
    agency_name: Optional[str] = None
    platform_name: Optional[str] = None
    specialist_name: Optional[str] = None
    model_config = {"from_attributes": True}
