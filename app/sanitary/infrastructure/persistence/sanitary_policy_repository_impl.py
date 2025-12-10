from typing import List, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.connection import Base
from app.sanitary.application.ports.sanitary_policy_repository import (
    SanitaryPolicyRepository,
)
from app.sanitary.domain.sanitary_policy import SanitaryPolicy

class SanitaryPolicyModel(Base):
    """
    Modelo ORM para la entidad PoliticaSanidad.

    Tabla sugerida: sanitary_policies
      - id (UUID, PK)
      - name (nombre)
      - description (descripcion)
      - is_active (esta_activa)
    """

    __tablename__ = "sanitary_policies"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(sa.String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)


class PostgreSQLSanitaryPolicyRepository(SanitaryPolicyRepository):
    """
    Implementación PostgreSQL de SanitaryPolicyRepository usando AsyncSession.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------
    # Helpers internos
    # -------------
    @staticmethod
    def _to_domain(model: SanitaryPolicyModel) -> SanitaryPolicy:
        return SanitaryPolicy(
            id=model.id,
            name=model.name,
            description=model.description,
            is_active=model.is_active,
        )

    @staticmethod
    def _to_model(policy: SanitaryPolicy) -> dict:
        return {
            "id": policy.id,
            "name": policy.name,
            "description": policy.description,
            "is_active": policy.is_active,
        }

    # -------------
    # Métodos del puerto
    # -------------
    async def get_by_id(self, policy_id: UUID) -> Optional[SanitaryPolicy]:
        stmt = select(SanitaryPolicyModel).where(SanitaryPolicyModel.id == policy_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_domain(model)

    async def list_all(self) -> List[SanitaryPolicy]:
        stmt = select(SanitaryPolicyModel).order_by(SanitaryPolicyModel.name.asc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def list_active(self) -> List[SanitaryPolicy]:
        stmt = (
            select(SanitaryPolicyModel)
            .where(SanitaryPolicyModel.is_active.is_(True))
            .order_by(SanitaryPolicyModel.name.asc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def save(self, policy: SanitaryPolicy) -> SanitaryPolicy:
        """
        Crea o actualiza una política.
        Si el ID ya existe, actualiza; si no, inserta.
        """
        existing = await self._session.get(SanitaryPolicyModel, policy.id)
        if existing:
            # update
            existing.name = policy.name
            existing.description = policy.description
            existing.is_active = policy.is_active
            model = existing
        else:
            # insert
            model = SanitaryPolicyModel(**self._to_model(policy))
            self._session.add(model)

        await self._session.flush()
        return self._to_domain(model)
