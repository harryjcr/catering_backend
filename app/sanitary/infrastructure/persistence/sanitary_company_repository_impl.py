from typing import List, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.connection import Base
from app.sanitary.application.ports.sanitary_company_repository import (
    SanitaryCompanyRepository,
)
from app.sanitary.domain.sanitary_company import SanitaryCompany

class SanitaryCompanyModel(Base):
    """
    Modelo ORM para la entidad Empresa del módulo de sanidad.

    Tabla sugerida: sanitary_companies
      - id (UUID, PK)          -> empresa_id
      - business_name          -> razon_social
      - ruc                    -> ruc
      - phone                  -> telefono
      - email                  -> correo
    """

    __tablename__ = "sanitary_companies"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
    )
    business_name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    ruc: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(sa.String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(sa.String(150), nullable=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "ruc",
            name="uq_sanitary_companies_ruc",
        ),
    )


class PostgreSQLSanitaryCompanyRepository(SanitaryCompanyRepository):
    """
    Implementación PostgreSQL de SanitaryCompanyRepository usando AsyncSession.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------
    # Helpers internos
    # -------------
    @staticmethod
    def _to_domain(model: SanitaryCompanyModel) -> SanitaryCompany:
        return SanitaryCompany(
            id=model.id,
            business_name=model.business_name,
            ruc=model.ruc,
            phone=model.phone,
            email=model.email,
        )

    @staticmethod
    def _to_model_dict(company: SanitaryCompany) -> dict:
        return {
            "id": company.id,
            "business_name": company.business_name,
            "ruc": company.ruc,
            "phone": company.phone,
            "email": company.email,
        }

    # -------------
    # Métodos del puerto
    # -------------
    async def get_by_id(self, company_id: UUID) -> Optional[SanitaryCompany]:
        model = await self._session.get(SanitaryCompanyModel, company_id)
        if not model:
            return None
        return self._to_domain(model)

    async def list_all(self) -> List[SanitaryCompany]:
        """
        Lista todas las empresas disponibles para ser contactadas.
        """
        stmt = select(SanitaryCompanyModel).order_by(
            SanitaryCompanyModel.business_name.asc()
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def save(self, company: SanitaryCompany) -> SanitaryCompany:
        """
        Crea o actualiza una empresa de sanidad.
        """
        existing = await self._session.get(SanitaryCompanyModel, company.id)
        if existing:
            existing.business_name = company.business_name
            existing.ruc = company.ruc
            existing.phone = company.phone
            existing.email = company.email
            model = existing
        else:
            model = SanitaryCompanyModel(**self._to_model_dict(company))
            self._session.add(model)

        await self._session.flush()
        return self._to_domain(model)
