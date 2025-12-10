"""Implementación PostgreSQL del repositorio de TimeOffRequest"""
from typing import Optional, List
from datetime import date, datetime, timezone
import uuid

import sqlalchemy as sa
from sqlalchemy import Column, String, Date, Integer, DateTime, JSON
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import UUID

from app.shared.database.connection import Base
from app.requests.domain.time_off_request import TimeOffRequest
from app.requests.domain.request_status import RequestStatus, RequestType
from app.requests.application.ports.time_off_request_repository import TimeOffRequestRepository


class TimeOffRequestModel(Base):
    """Modelo SQLAlchemy para solicitudes de tiempo libre"""
    __tablename__ = "time_off_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    type = Column(String(50), nullable=False)         # "vacation" | "permission"
    status = Column(String(50), nullable=False)       # "pending" | "approved" | "rejected" | "cancelled"

    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    days_requested = Column(Integer, nullable=False)

    reason = Column(String(500), nullable=True)
    audit = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text('now()'))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text('now()'))


class PostgreSQLTimeOffRequestRepository(TimeOffRequestRepository):
    """Implementación PostgreSQL del repositorio de solicitudes de tiempo libre"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, req: TimeOffRequest) -> TimeOffRequest:
        from sqlalchemy.dialects.postgresql import UUID as PG_UUID  # por si lo necesitas
        stmt = select(TimeOffRequestModel).where(
            TimeOffRequestModel.id == (uuid.UUID(req.id) if req.id else sa.null())
        )
        result = await self.session.execute(stmt)
        db_req = result.scalar_one_or_none()

        if db_req:
            data = self._to_dict(req)
            for k, v in data.items():
                setattr(db_req, k, v)
            db_req.updated_at = datetime.now(timezone.utc)
        else:
            db_req = TimeOffRequestModel(
                id=uuid.uuid4() if not req.id else uuid.UUID(req.id),
                **self._to_dict(req)
            )
            self.session.add(db_req)

        await self.session.commit()
        await self.session.refresh(db_req)
        return self._to_domain(db_req)


    async def find_by_id(self, request_id: str) -> Optional[TimeOffRequest]:
        stmt = select(TimeOffRequestModel).where(TimeOffRequestModel.id == UUID(request_id))
        result = await self.session.execute(stmt)
        db_req = result.scalar_one_or_none()
        return self._to_domain(db_req) if db_req else None

    async def find_by_user(self, user_id: str, limit: int = 50) -> List[TimeOffRequest]:
        stmt = (
            select(TimeOffRequestModel)
            .where(TimeOffRequestModel.user_id == UUID(user_id))
            .order_by(TimeOffRequestModel.start_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        return [self._to_domain(r) for r in items]

    async def find_overlaps(self, user_id: str, start: date, end: date) -> List[TimeOffRequest]:
        """
        Devuelve solicitudes del usuario que se solapan con [start, end].
        Regla de solape: (start <= end_date) AND (end >= start_date)
        """
        stmt = (
            select(TimeOffRequestModel)
            .where(TimeOffRequestModel.user_id == UUID(user_id))
            .where(TimeOffRequestModel.start_date <= end)
            .where(TimeOffRequestModel.end_date >= start)
        )
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        return [self._to_domain(r) for r in items]

    # ---------- helpers ----------
    def _to_dict(self, req: TimeOffRequest) -> dict:
        return {
            "user_id": uuid.UUID(req.user_id),
            "type": req.type.value,
            "status": req.status.value,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "days_requested": req.days_requested,
            "reason": req.reason,
            "audit": req.audit or {},
            "created_at": req.created_at,
            "updated_at": req.updated_at,
        }

    def _to_domain(self, m: TimeOffRequestModel) -> TimeOffRequest:
        return TimeOffRequest(
            id=str(m.id),
            user_id=str(m.user_id),
            type=RequestType(m.type),
            start_date=m.start_date,
            end_date=m.end_date,
            days_requested=m.days_requested,
            status=RequestStatus(m.status),
            reason=m.reason,
            audit=m.audit or {},
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
