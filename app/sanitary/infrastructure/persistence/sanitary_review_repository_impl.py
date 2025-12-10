from datetime import date
from typing import List, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.connection import Base
from app.sanitary.application.ports.sanitary_review_repository import (
    SanitaryReviewRepository,
)
from app.sanitary.domain.sanitary_review import SanitaryReview

class SanitaryReviewModel(Base):
    """
    Modelo ORM para la entidad RevisionSanidad.

    Tabla sugerida: sanitary_reviews
      - id (UUID, PK)                        -> revision_id
      - policy_id (UUID, FK sanitary_policies.id)       -> politica_id
      - user_id (UUID, FK users.id)                      -> usuario_id
      - date (DATE)                                     -> fecha
      - is_conform (BOOLEAN)                            -> es_conforme
      - observation (TEXT)                              -> observacion
      - incident_type_id (UUID, FK sanitary_incident_types.id, NULL) -> tipo_incidencia_id
      - company_id (UUID, FK sanitary_companies.id, NULL)            -> empresa_id
        (empresa a contactar en caso de inconformidad)
    """

    __tablename__ = "sanitary_reviews"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
    )

    policy_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        sa.ForeignKey("sanitary_policies.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    date: Mapped[date] = mapped_column(sa.Date, nullable=False)

    is_conform: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
    )

    observation: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
    )

    incident_type_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        sa.ForeignKey("sanitary_incident_types.id", ondelete="SET NULL"),
        nullable=True,
    )

    company_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        sa.ForeignKey("sanitary_companies.id", ondelete="SET NULL"),
        nullable=True,
    )


class PostgreSQLSanitaryReviewRepository(SanitaryReviewRepository):
    """
    Implementación PostgreSQL de SanitaryReviewRepository usando AsyncSession.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------
    # Helpers internos
    # -------------
    @staticmethod
    def _to_domain(model: SanitaryReviewModel) -> SanitaryReview:
        return SanitaryReview(
            id=model.id,
            policy_id=model.policy_id,
            user_id=model.user_id,
            date=model.date,
            is_conform=model.is_conform,
            observation=model.observation,
            incident_type_id=model.incident_type_id,
            company_id=model.company_id,
        )

    @staticmethod
    def _to_model_dict(review: SanitaryReview) -> dict:
        return {
            "id": review.id,
            "policy_id": review.policy_id,
            "user_id": review.user_id,
            "date": review.date,
            "is_conform": review.is_conform,
            "observation": review.observation,
            "incident_type_id": review.incident_type_id,
            "company_id": review.company_id,
        }

    # -------------
    # Métodos del puerto
    # -------------
    async def get_by_id(self, review_id: UUID) -> Optional[SanitaryReview]:
        model = await self._session.get(SanitaryReviewModel, review_id)
        if not model:
            return None
        return self._to_domain(model)

    async def save(self, review: SanitaryReview) -> SanitaryReview:
        """
        Crea una nueva revisión en la base de datos o actualiza si ya existe
        (aunque en la práctica normalmente solo se crean).
        """
        existing = await self._session.get(SanitaryReviewModel, review.id)
        if existing:
            existing.policy_id = review.policy_id
            existing.user_id = review.user_id
            existing.date = review.date
            existing.is_conform = review.is_conform
            existing.observation = review.observation
            existing.incident_type_id = review.incident_type_id
            existing.company_id = review.company_id
            model = existing
        else:
            model = SanitaryReviewModel(**self._to_model_dict(review))
            self._session.add(model)

        await self._session.flush()
        # Don't commit here - let the context manager handle it
        return self._to_domain(model)

    async def list_by_policy_and_period(
        self,
        policy_id: UUID,
        start_date: date,
        end_date: date,
    ) -> List[SanitaryReview]:
        """
        Lista las revisiones de una política entre start_date y end_date (incluidos),
        ordenadas por fecha descendente (para el historial en la UI).
        """
        stmt = (
            select(SanitaryReviewModel)
            .where(SanitaryReviewModel.policy_id == policy_id)
            .where(SanitaryReviewModel.date >= start_date)
            .where(SanitaryReviewModel.date <= end_date)
            .order_by(SanitaryReviewModel.date.desc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def get_last_by_policy(self, policy_id: UUID) -> Optional[SanitaryReview]:
        """
        Devuelve la última revisión de una política (por fecha).
        Se usará para calcular 'próxima revisión = fecha_última + 30 días'
        en el caso de uso, sin almacenar ese dato en la BD.
        """
        stmt = (
            select(SanitaryReviewModel)
            .where(SanitaryReviewModel.policy_id == policy_id)
            .order_by(SanitaryReviewModel.date.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None
