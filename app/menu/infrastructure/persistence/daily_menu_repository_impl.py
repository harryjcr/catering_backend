import uuid
from datetime import date, datetime
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import Column, Date, String, Boolean, DateTime, text

from app.shared.database.connection import Base

from app.menu.application.ports.daily_menu_repository import DailyMenuRepository
from app.menu.domain.daily_menu import DailyMenu



class DailyMenuModel(Base):
    __tablename__ = "daily_menus"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    weekly_menu_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    day_of_week = Column(String(20), nullable=True)
    is_holiday = Column(
        Boolean,
        nullable=False,
        server_default=sa.text("false"),
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "weekly_menu_id",
            "date",
            name="uq_daily_menus_week_date",
        ),
    )


class PostgreSQLDailyMenuRepository(DailyMenuRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.session_factory = async_sessionmaker(
            bind=session.bind,
            expire_on_commit=False,
        )

    def _to_domain(self, m: DailyMenuModel) -> DailyMenu:
        return DailyMenu(
            id=str(m.id),
            weekly_menu_id=str(m.weekly_menu_id),
            date=m.date,
            day_of_week=m.day_of_week,
            is_holiday=bool(m.is_holiday),
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    async def bulk_replace_for_week(
        self,
        weekly_menu_id: str,
        days: List[DailyMenu],
    ) -> None:
        wid = uuid.UUID(str(weekly_menu_id))

        async with self.session_factory() as session:
            async with session.begin():
                # 1) borrar días anteriores de esa semana
                await session.execute(
                    sa.delete(DailyMenuModel).where(
                        DailyMenuModel.weekly_menu_id == wid
                    )
                )

                # 2) insertar días nuevos
                for d in days:
                    did = uuid.UUID(d.id) if d.id else uuid.uuid4()
                    model = DailyMenuModel(
                        id=did,
                        weekly_menu_id=wid,
                        date=d.date,
                        day_of_week=d.day_of_week,
                        is_holiday=bool(d.is_holiday),
                        created_at=d.created_at,
                        updated_at=d.updated_at,
                    )
                    session.add(model)

    async def list_by_week(self, weekly_menu_id: str) -> List[DailyMenu]:
        stmt = (
            select(DailyMenuModel)
            .where(DailyMenuModel.weekly_menu_id == uuid.UUID(str(weekly_menu_id)))
            .order_by(DailyMenuModel.date.asc())
        )
        r = await self.session.execute(stmt)
        rows = r.scalars().all()
        return [self._to_domain(m) for m in rows]

    async def find_by_date(self, day: date) -> Optional[DailyMenu]:
        stmt = (
            select(DailyMenuModel)
            .where(DailyMenuModel.date == day)
            .order_by(DailyMenuModel.id.asc())
            .limit(1)
        )
        r = await self.session.execute(stmt)
        m = r.scalar_one_or_none()
        return self._to_domain(m) if m else None

    async def find_by_id(self, daily_menu_id: str) -> Optional[DailyMenu]:
        stmt = (
            select(DailyMenuModel)
            .where(DailyMenuModel.id == uuid.UUID(str(daily_menu_id)))
            .limit(1)
        )
        r = await self.session.execute(stmt)
        m = r.scalar_one_or_none()
        return self._to_domain(m) if m else None
