from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any


class BidResultCreate(BaseModel):
    bid_info_id: int
    our_price: float = 0
    competitors: list[dict] = []  # [{"org_id": 1, "price": 100000}]
    scoring_details: list[dict] = []
    deposit_status: Optional[str] = None
    is_won: bool = False
    lost_analysis: str = ""
    contract_number: str = ""
    contract_status: str = "无"
    contract_amount: float = 0
    notes: str = ""


class BidResultUpdate(BaseModel):
    our_price: Optional[float] = None
    competitors: Optional[list[dict]] = None
    scoring_details: Optional[list[dict]] = None
    deposit_status: Optional[str] = None
    is_won: Optional[bool] = None
    lost_analysis: Optional[str] = None
    contract_number: Optional[str] = None
    contract_status: Optional[str] = None
    contract_amount: Optional[float] = None
    notes: Optional[str] = None


class BidResultResponse(BaseModel):
    id: int
    bid_info_id: int
    our_price: float
    competitors: Any
    scoring_details: Any
    deposit_status: Optional[str]
    is_won: bool
    lost_analysis: str
    contract_number: str
    contract_status: str
    contract_amount: float
    notes: str
    created_at: datetime
    updated_at: datetime
    # Enriched
    project_name: Optional[str] = None
    model_config = {"from_attributes": True}
