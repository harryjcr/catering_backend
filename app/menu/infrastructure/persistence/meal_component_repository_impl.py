import uuid
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import Column, String, Integer, Float

from app.shared.database.connection import Base

from app.menu.application.ports.meal_component_repository import MealComponentRepository
from app.menu.domain.meal_component import MealComponent



class MealComponentModel(Base):
    __tablename__ = "meal_components"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    component_type_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    dish_name = Column(String(255), nullable=False)
    calories = Column(Float, nullable=True)
    order_position = Column(Integer, nullable=False, server_default="0")


class PostgreSQLMealComponentRepository(MealComponentRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.session_factory = async_sessionmaker(
            bind=session.bind,
            expire_on_commit=False,
        )

    def _to_domain(self, m: MealComponentModel) -> MealComponent:
        return MealComponent(
            id=str(m.id),
            meal_id=str(m.meal_id),
            component_type_id=str(m.component_type_id),
            dish_name=m.dish_name,
            calories=m.calories,
            order_position=m.order_position,
        )

    async def bulk_replace_for_meal(
        self,
        meal_id: str,
        components: List[MealComponent],
    ) -> None:
        mid = uuid.UUID(str(meal_id))

        async with self.session_factory() as session:
            async with session.begin():
                await session.execute(
                    sa.delete(MealComponentModel).where(
                        MealComponentModel.meal_id == mid
                    )
                )

                for c in components:
                    cid = uuid.UUID(c.id) if c.id else uuid.uuid4()
                    model = MealComponentModel(
                        id=cid,
                        meal_id=mid,
                        component_type_id=uuid.UUID(str(c.component_type_id)),
                        dish_name=c.dish_name,
                        calories=c.calories,
                        order_position=c.order_position,
                    )
                    session.add(model)

    async def list_by_meal(self, meal_id: str) -> List[MealComponent]:
        stmt = (
            select(MealComponentModel)
            .where(MealComponentModel.meal_id == uuid.UUID(str(meal_id)))
            .order_by(MealComponentModel.order_position.asc())
        )
        r = await self.session.execute(stmt)
        rows = r.scalars().all()
        return [self._to_domain(m) for m in rows]

    async def find_by_id(self, meal_component_id: str) -> Optional[MealComponent]:
        stmt = (
            select(MealComponentModel)
            .where(MealComponentModel.id == uuid.UUID(str(meal_component_id)))
            .limit(1)
        )
        r = await self.session.execute(stmt)
        m = r.scalar_one_or_none()
        return self._to_domain(m) if m else None
