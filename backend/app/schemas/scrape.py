from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class ScrapeRunResponse(BaseModel):
    id: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    triggered_by: Optional[int] = None
    triggered_by_name: Optional[str] = None
    status: str
    total_count: int = 0
    created_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    sites_summary: Any = {}
    error_summary: Any = {}
    model_config = {"from_attributes": True}


class ScrapeItemLogResponse(BaseModel):
    id: int
    run_id: int
    source: str
    external_no: Optional[str] = None
    project_name: str
    source_url: Optional[str] = None
    result: str
    project_id: Optional[int] = None
    skip_reason: Optional[str] = None
    error_message: Optional[str] = None
    processed_at: datetime
    model_config = {"from_attributes": True}


class ScrapeRunDetailResponse(ScrapeRunResponse):
    item_logs: list[ScrapeItemLogResponse] = []
