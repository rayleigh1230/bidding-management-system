import enum
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class OrgType(str, enum.Enum):
    ours = "ours"          # 我方公司
    external = "external"  # 外部单位


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    org_type: Mapped[str] = mapped_column(Enum(OrgType), default=OrgType.external)
    short_name: Mapped[str] = mapped_column(String(100), default="")
    contact_person: Mapped[str] = mapped_column(String(50), default="")
    contact_phone: Mapped[str] = mapped_column(String(20), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
