"""Implementación PostgreSQL del repositorio de intercambio de turnos"""
from typing import Optional, List
from datetime import datetime, timezone
import uuid

import sqlalchemy as sa
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import UUID

from app.shared.database.connection import Base
from app.requests.domain.shift_swap_request import ShiftSwapRequest
from app.requests.domain.request_status import SwapStatus
from app.requests.application.ports.shift_swap_repository import ShiftSwapRepository


class ShiftSwapRequestModel(Base):
    __tablename__ = "shift_swap_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    requester_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    target_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    requester_shift_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    target_shift_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    status = Column(String(50), nullable=False)  # pending|accepted|rejected|cancelled
    note = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text('now()'))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text('now()'))
    responded_at = Column(DateTime(timezone=True), nullable=True)


class PostgreSQLShiftSwapRepository(ShiftSwapRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, swap: ShiftSwapRequest) -> ShiftSwapRequest:
        stmt = select(ShiftSwapRequestModel).where(
            ShiftSwapRequestModel.id == (uuid.UUID(swap.id) if swap.id else sa.null())
        )
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()

        if m:
            data = self._to_dict(swap)
            for k, v in data.items():
                setattr(m, k, v)
            m.updated_at = datetime.now(timezone.utc)
        else:
            m = ShiftSwapRequestModel(
                id=uuid.uuid4() if not swap.id else uuid.UUID(swap.id),
                **self._to_dict(swap)
            )
            self.session.add(m)

        await self.session.commit()
        await self.session.refresh(m)
        return self._to_domain(m)

    async def find_by_id(self, swap_id: str) -> Optional[ShiftSwapRequest]:
        stmt = select(ShiftSwapRequestModel).where(ShiftSwapRequestModel.id == UUID(swap_id))
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()
        return self._to_domain(m) if m else None

    async def find_my_swaps(self, user_id: str, limit: int = 50) -> List[ShiftSwapRequest]:
        stmt = (
            select(ShiftSwapRequestModel)
            .where(
                (ShiftSwapRequestModel.requester_user_id == UUID(user_id)) |
                (ShiftSwapRequestModel.target_user_id == UUID(user_id))
            )
            .order_by(ShiftSwapRequestModel.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        return [self._to_domain(m) for m in items]

    # ---------- helpers ----------
    def _to_dict(self, s: ShiftSwapRequest) -> dict:
        return {
            "requester_user_id": uuid.UUID(s.requester_user_id),
            "target_user_id": uuid.UUID(s.target_user_id),
            "requester_shift_id": uuid.UUID(s.requester_shift_id),
            "target_shift_id": uuid.UUID(s.target_shift_id),
            "status": s.status.value,
            "note": s.note,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
            "responded_at": s.responded_at,
        }

    def _to_domain(self, m: ShiftSwapRequestModel) -> ShiftSwapRequest:
        return ShiftSwapRequest(
            id=str(m.id),
            requester_user_id=str(m.requester_user_id),
            target_user_id=str(m.target_user_id),
            requester_shift_id=str(m.requester_shift_id),
            target_shift_id=str(m.target_shift_id),
            status=SwapStatus(m.status),
            note=m.note,
            created_at=m.created_at,
            updated_at=m.updated_at,
            responded_at=m.responded_at,
        )
