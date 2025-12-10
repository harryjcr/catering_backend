import uuid
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.connection import Base

from app.menu.application.ports.component_type_repository import (
    ComponentTypeRepository,
)
from app.menu.domain.component_type import ComponentType


class ComponentTypeModel(Base):
    __tablename__ = "component_types"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    component_name: Mapped[str] = mapped_column(
        sa.String(100),
        nullable=False,
        unique=True,
    )
    display_order: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "component_name",
            name="uq_component_types_name",
        ),
    )


class PostgreSQLComponentTypeRepository(ComponentTypeRepository):
    """
    Implementación PostgreSQL para la tabla component_types.
    Usa el mismo Base y patrón que el resto de repos de menú.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ==============
    # Helpers internos
    # ==============
    @staticmethod
    def _to_domain(model: ComponentTypeModel) -> ComponentType:
        return ComponentType(
            id=str(model.id),
            name=model.component_name,
            display_order=model.display_order,
        )

    # ==============
    # Métodos del puerto
    # ==============
    async def get_by_name(self, name: str) -> Optional[ComponentType]:
        stmt = (
            select(ComponentTypeModel)
            .where(ComponentTypeModel.component_name == name)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_all(self) -> List[ComponentType]:
        stmt = (
            select(ComponentTypeModel)
            .order_by(
                ComponentTypeModel.display_order.asc(),
                ComponentTypeModel.component_name.asc(),
            )
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def create(self, component_type: ComponentType) -> ComponentType:
        """
        Crea un nuevo tipo de componente. Si no tiene display_order (>0),
        se asigna automáticamente como max(display_order) + 1.
        """
        # Resolver id
        if component_type.id:
            cid = uuid.UUID(str(component_type.id))
        else:
            cid = uuid.uuid4()
            component_type.id = str(cid)

        # Resolver display_order
        if not component_type.display_order or component_type.display_order <= 0:
            stmt = select(sa.func.max(ComponentTypeModel.display_order))
            result = await self._session.execute(stmt)
            max_order = result.scalar() or 0
            component_type.display_order = max_order + 1

        model = ComponentTypeModel(
            id=cid,
            component_name=component_type.name,
            display_order=component_type.display_order,
        )
        self._session.add(model)
        # No hacemos commit aquí; lo controla el servicio/use case
        await self._session.flush()

        return component_type
