"""Implementación PostgreSQL del repositorio de saldos de vacaciones"""
from typing import Optional
from datetime import datetime, timezone
import uuid

import sqlalchemy as sa
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import UUID

from app.shared.database.connection import Base
from app.requests.domain.vacation_balance import VacationBalance
from app.requests.application.ports.vacation_balance_repository import VacationBalanceRepository


class VacationBalanceModel(Base):
    __tablename__ = "vacation_balances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)

    total_days = Column(Integer, nullable=False, default=0)
    carried_over_days = Column(Integer, nullable=False, default=0)
    used_days = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text('now()'))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text('now()'))


class PostgreSQLVacationBalanceRepository(VacationBalanceRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_for_user_year(self, user_id: str, year: int) -> Optional[VacationBalance]:
        stmt = select(VacationBalanceModel).where(
            VacationBalanceModel.user_id == UUID(user_id),
            VacationBalanceModel.year == year
        )
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()
        return self._to_domain(m) if m else None

    async def save(self, balance: VacationBalance) -> VacationBalance:
        stmt = select(VacationBalanceModel).where(
            VacationBalanceModel.id == (uuid.UUID(balance.id) if balance.id else sa.null())
        )
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()

        if m:
            data = self._to_dict(balance)
            for k, v in data.items():
                setattr(m, k, v)
            m.updated_at = datetime.now(timezone.utc)
        else:
            m = VacationBalanceModel(
                id=uuid.uuid4() if not balance.id else uuid.UUID(balance.id),
                **self._to_dict(balance)
            )
            self.session.add(m)

        await self.session.commit()
        await self.session.refresh(m)
        return self._to_domain(m)

    # ---------- helpers ----------
    def _to_dict(self, b: VacationBalance) -> dict:
        return {
            "user_id": uuid.UUID(b.user_id),
            "year": b.year,
            "total_days": b.total_days,
            "used_days": b.used_days,
            "carried_over_days": b.carried_over_days,
            "created_at": b.created_at,
            "updated_at": b.updated_at,
        }

    def _to_domain(self, m: VacationBalanceModel) -> VacationBalance:
        return VacationBalance(
            id=str(m.id),
            user_id=str(m.user_id),
            year=m.year,
            total_days=m.total_days,
            used_days=m.used_days,
            carried_over_days=m.carried_over_days,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
