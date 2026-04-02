from datetime import datetime

from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # create/update/delete/advance/abandon
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # project/bidding_info/bid_info/bid_result
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")  # JSON detail
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
