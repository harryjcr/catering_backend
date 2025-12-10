import uuid
import sqlalchemy as sa
from typing import Optional, List
from datetime import date, datetime

from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import Column, Date, String, DateTime

from app.shared.database.connection import Base

from app.menu.application.ports.menu_change_repository import MenuChangeRepository
from app.menu.domain.menu_change_request import MenuChangeRequest
from app.menu.domain.menu_enums import MealType, ChangeStatus


class MenuChangeModel(Base):
    __tablename__ = "menu_change_requests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    daily_menu_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    day_date = Column(Date, nullable=False, index=True)
    meal_type = Column(String(20), nullable=False)
    old_value = Column(String(255), nullable=False, default="")
    new_value = Column(String(255), nullable=False)
    reason = Column(String(500), nullable=False)

    status = Column(String(30), nullable=False, index=True, default=ChangeStatus.PENDING.value)
    requested_by = Column(PG_UUID(as_uuid=True), nullable=False)
    decided_by = Column(PG_UUID(as_uuid=True), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    notes_from_decider = Column(String(500), nullable=True)

    batch_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

class PostgreSQLMenuChangeRepository(MenuChangeRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(self, m: MenuChangeModel) -> MenuChangeRequest:
        return MenuChangeRequest(
            id=str(m.id),
            daily_menu_id=str(m.daily_menu_id),
            day_date=m.day_date,
            meal_type=MealType(m.meal_type),
            old_value=m.old_value,
            new_value=m.new_value,
            reason=m.reason,
            status=ChangeStatus(m.status),
            requested_by=str(m.requested_by),
            decided_by=str(m.decided_by) if m.decided_by else None,
            decided_at=m.decided_at,
            notes_from_decider=m.notes_from_decider,
            batch_id=str(m.batch_id) if m.batch_id else None,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    async def save(self, req: MenuChangeRequest) -> MenuChangeRequest:
        if req.id:
            stmt = select(MenuChangeModel).where(MenuChangeModel.id == uuid.UUID(req.id)).limit(1)
            r = await self.session.execute(stmt)
            m = r.scalar_one()
            m.status = req.status.value
            m.decided_by = uuid.UUID(req.decided_by) if req.decided_by else None
            m.decided_at = req.decided_at
            m.notes_from_decider = req.notes_from_decider
            m.updated_at = datetime.utcnow()
            await self.session.flush()
            return self._to_domain(m)

        m = MenuChangeModel(
            daily_menu_id=uuid.UUID(req.daily_menu_id),
            day_date=req.day_date,
            meal_type=req.meal_type.value,
            old_value=req.old_value,
            new_value=req.new_value,
            reason=req.reason,
            status=req.status.value,
            requested_by=uuid.UUID(req.requested_by),
            decided_by=uuid.UUID(req.decided_by) if req.decided_by else None,
            decided_at=req.decided_at,
            notes_from_decider=req.notes_from_decider,
            batch_id=uuid.UUID(req.batch_id) if req.batch_id else None,
        )
        self.session.add(m)
        await self.session.flush()
        return self._to_domain(m)

    async def find_by_id(self, change_id: str) -> Optional[MenuChangeRequest]:
        stmt = select(MenuChangeModel).where(MenuChangeModel.id == uuid.UUID(change_id)).limit(1)
        r = await self.session.execute(stmt)
        m = r.scalar_one_or_none()
        return self._to_domain(m) if m else None

    async def list_for_month(self, year: int, month: int) -> List[MenuChangeRequest]:
        stmt = select(MenuChangeModel).where(
            sa.extract("year", MenuChangeModel.day_date) == year,
            sa.extract("month", MenuChangeModel.day_date) == month
        ).order_by(MenuChangeModel.created_at.asc())
        r = await self.session.execute(stmt)
        rows = r.scalars().all()
        return [self._to_domain(m) for m in rows]

    async def list_by_batch(self, batch_id: str) -> List[MenuChangeRequest]:
        stmt = select(MenuChangeModel).where(MenuChangeModel.batch_id == uuid.UUID(batch_id))
        r = await self.session.execute(stmt)
        rows = r.scalars().all()
        return [self._to_domain(m) for m in rows]
