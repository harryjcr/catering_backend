import uuid
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import Column, Integer, String

from app.shared.database.connection import Base

from app.menu.application.ports.weekly_menu_repository import WeeklyMenuRepository
from app.menu.domain.weekly_menu import WeeklyMenu



class WeeklyMenuModel(Base):
    __tablename__ = "weekly_menus"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    monthly_menu_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    week_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "monthly_menu_id",
            "week_number",
            name="uq_weekly_menus_month_week",
        ),
    )


class PostgreSQLWeeklyMenuRepository(WeeklyMenuRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.session_factory = async_sessionmaker(
            bind=session.bind,
            expire_on_commit=False,
        )

    def _to_domain(self, m: WeeklyMenuModel) -> WeeklyMenu:
        return WeeklyMenu(
            id=str(m.id),
            monthly_menu_id=str(m.monthly_menu_id),
            week_number=m.week_number,
            title=m.title,
        )

    async def bulk_replace(
        self,
        monthly_menu_id: str,
        weeks: List[WeeklyMenu],
    ) -> None:
        mid = uuid.UUID(str(monthly_menu_id))

        async with self.session_factory() as session:
            async with session.begin():
                # 1) borrar semanas anteriores de ese mes
                await session.execute(
                    sa.delete(WeeklyMenuModel).where(
                        WeeklyMenuModel.monthly_menu_id == mid
                    )
                )

                # 2) insertar nuevas semanas
                for w in weeks:
                    wid = uuid.UUID(w.id) if w.id else uuid.uuid4()
                    model = WeeklyMenuModel(
                        id=wid,
                        monthly_menu_id=mid,
                        week_number=w.week_number,
                        title=w.title,
                    )
                    session.add(model)

    async def list_by_month(self, monthly_menu_id: str) -> List[WeeklyMenu]:
        stmt = (
            select(WeeklyMenuModel)
            .where(WeeklyMenuModel.monthly_menu_id == uuid.UUID(str(monthly_menu_id)))
            .order_by(WeeklyMenuModel.week_number.asc())
        )
        r = await self.session.execute(stmt)
        rows = r.scalars().all()
        return [self._to_domain(m) for m in rows]

    async def find_by_id(self, weekly_menu_id: str) -> Optional[WeeklyMenu]:
        stmt = (
            select(WeeklyMenuModel)
            .where(WeeklyMenuModel.id == uuid.UUID(str(weekly_menu_id)))
            .limit(1)
        )
        r = await self.session.execute(stmt)
        m = r.scalar_one_or_none()
        return self._to_domain(m) if m else None
