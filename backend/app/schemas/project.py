from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any


class ProjectCreate(BaseModel):
    bidding_type: str
    project_name: str
    bidding_unit_id: Optional[int] = None
    region: str = ""  # JSON string like '["浙江省","杭州市","西湖区"]'
    manager_ids: list[int] = []
    description: str = ""


class ProjectUpdate(BaseModel):
    bidding_type: Optional[str] = None
    project_name: Optional[str] = None
    bidding_unit_id: Optional[int] = None
    region: Optional[str] = None
    manager_ids: Optional[list[int]] = None
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    bidding_type: str
    project_name: str
    bidding_unit_id: Optional[int]
    region: str
    manager_ids: Any
    status: str
    description: str
    abandon_reason: str
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    # Enriched fields (populated by API)
    bidding_unit_name: Optional[str] = None
    manager_names: Optional[list[str]] = None
    model_config = {"from_attributes": True}
