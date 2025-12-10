import uuid
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import Column, String, Float

from app.shared.database.connection import Base

from app.menu.application.ports.meal_repository import MealRepository
from app.menu.domain.meal import Meal
from app.menu.domain.menu_enums import MealType



class MealModel(Base):
    __tablename__ = "meals"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    daily_menu_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    meal_type = Column(String(20), nullable=False)
    total_kcal = Column(Float, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "daily_menu_id",
            "meal_type",
            name="uq_meals_daily_type",
        ),
    )


class PostgreSQLMealRepository(MealRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.session_factory = async_sessionmaker(
            bind=session.bind,
            expire_on_commit=False,
        )

    def _to_domain(self, m: MealModel) -> Meal:
        return Meal(
            id=str(m.id),
            daily_menu_id=str(m.daily_menu_id),
            meal_type=MealType(m.meal_type),
            total_kcal=m.total_kcal,
        )

    async def bulk_replace_for_daily_menu(
        self,
        daily_menu_id: str,
        meals: List[Meal],
    ) -> None:
        did = uuid.UUID(str(daily_menu_id))

        async with self.session_factory() as session:
            async with session.begin():
                await session.execute(
                    sa.delete(MealModel).where(MealModel.daily_menu_id == did)
                )

                for m in meals:
                    mid = uuid.UUID(m.id) if m.id else uuid.uuid4()
                    model = MealModel(
                        id=mid,
                        daily_menu_id=did,
                        meal_type=m.meal_type.value,
                        total_kcal=m.total_kcal,
                    )
                    session.add(model)

    async def list_by_daily_menu(self, daily_menu_id: str) -> List[Meal]:
        stmt = (
            select(MealModel)
            .where(MealModel.daily_menu_id == uuid.UUID(str(daily_menu_id)))
            .order_by(MealModel.meal_type.asc())
        )
        r = await self.session.execute(stmt)
        rows = r.scalars().all()
        return [self._to_domain(m) for m in rows]

    async def find_by_daily_and_type(
        self,
        daily_menu_id: str,
        meal_type: MealType,
    ) -> Optional[Meal]:
        stmt = (
            select(MealModel)
            .where(
                MealModel.daily_menu_id == uuid.UUID(str(daily_menu_id)),
                MealModel.meal_type == meal_type.value,
            )
            .limit(1)
        )
        r = await self.session.execute(stmt)
        m = r.scalar_one_or_none()
        return self._to_domain(m) if m else None

    async def find_by_id(self, meal_id: str) -> Optional[Meal]:
        stmt = (
            select(MealModel)
            .where(MealModel.id == uuid.UUID(str(meal_id)))
            .limit(1)
        )
        r = await self.session.execute(stmt)
        m = r.scalar_one_or_none()
        return self._to_domain(m) if m else None
