from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# Organization schemas
class OrganizationCreate(BaseModel):
    name: str
    short_name: str = ""
    contact_person: str = ""
    contact_phone: str = ""
    notes: str = ""
    org_type: str = "external"


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None
    org_type: Optional[str] = None


class OrganizationResponse(BaseModel):
    id: int
    name: str
    short_name: str
    contact_person: str
    contact_phone: str
    notes: str
    org_type: str
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# Platform schemas
class PlatformCreate(BaseModel):
    name: str
    url: str = ""


class PlatformUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None


class PlatformResponse(BaseModel):
    id: int
    name: str
    url: str
    created_at: datetime
    model_config = {"from_attributes": True}


# Manager schemas
class ManagerCreate(BaseModel):
    name: str
    phone: str = ""
    company: str = ""
    notes: str = ""


class ManagerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None


class ManagerResponse(BaseModel):
    id: int
    name: str
    phone: str
    company: str
    notes: str
    created_at: datetime
    model_config = {"from_attributes": True}
