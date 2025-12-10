from typing import List, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.connection import Base
from app.sanitary.application.ports.incident_type_repository import (
    IncidentTypeRepository,
)
from app.sanitary.domain.incident_type import IncidentType

class IncidentTypeModel(Base):
    """
    Modelo ORM para la entidad TipoIncidencia.

    Tabla sugerida: sanitary_incident_types
      - id (UUID, PK)                -> tipo_incidencia_id
      - policy_id (UUID, FK)         -> politica_id
      - name (VARCHAR)               -> nombre
      - description (TEXT)           -> descripcion
      - is_active (BOOLEAN)          -> esta_activa
    """

    __tablename__ = "sanitary_incident_types"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
    )
    policy_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        sa.ForeignKey("sanitary_policies.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(sa.String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "policy_id",
            "name",
            name="uq_sanitary_incident_types_policy_name",
        ),
    )


class PostgreSQLIncidentTypeRepository(IncidentTypeRepository):
    """
    Implementación PostgreSQL de IncidentTypeRepository usando AsyncSession.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------
    # Helpers internos
    # -------------
    @staticmethod
    def _to_domain(model: IncidentTypeModel) -> IncidentType:
        return IncidentType(
            id=model.id,
            policy_id=model.policy_id,
            name=model.name,
            description=model.description,
            is_active=model.is_active,
        )

    @staticmethod
    def _to_model_dict(incident_type: IncidentType) -> dict:
        return {
            "id": incident_type.id,
            "policy_id": incident_type.policy_id,
            "name": incident_type.name,
            "description": incident_type.description,
            "is_active": incident_type.is_active,
        }

    # -------------
    # Métodos del puerto
    # -------------
    async def get_by_id(self, incident_type_id: UUID) -> Optional[IncidentType]:
        model = await self._session.get(IncidentTypeModel, incident_type_id)
        if not model:
            return None
        return self._to_domain(model)

    async def list_by_policy(self, policy_id: UUID, only_active: bool = True) -> List[IncidentType]:
        stmt = select(IncidentTypeModel).where(IncidentTypeModel.policy_id == policy_id)

        if only_active:
            stmt = stmt.where(IncidentTypeModel.is_active.is_(True))

        stmt = stmt.order_by(IncidentTypeModel.name.asc())

        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def save(self, incident_type: IncidentType) -> IncidentType:
        """
        Crea o actualiza un tipo de incidencia.
        Si el ID ya existe, actualiza; si no, inserta.
        """
        existing = await self._session.get(IncidentTypeModel, incident_type.id)
        if existing:
            existing.name = incident_type.name
            existing.description = incident_type.description
            existing.is_active = incident_type.is_active
            model = existing
        else:
            model = IncidentTypeModel(**self._to_model_dict(incident_type))
            self._session.add(model)

        await self._session.flush()
        return self._to_domain(model)
