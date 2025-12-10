from typing import Optional
from datetime import datetime, timezone
from app.users.domain.activation_token import ActivationToken
from app.users.application.ports.activation_token_repository import ActivationTokenRepository
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import UUID
import uuid
import sqlalchemy as sa

from app.shared.database.connection import Base


class ActivationTokenModel(Base):
    """Modelo SQLAlchemy para tokens de activación"""
    __tablename__ = "activation_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    employee_id = Column(String(50), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    is_used = Column(Boolean, default=False)


class PostgreSQLActivationTokenRepository(ActivationTokenRepository):
    """Implementación del repositorio de tokens para PostgreSQL"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, token: ActivationToken) -> ActivationToken:
        """Guarda un token de activación"""
        stmt = select(ActivationTokenModel).where(ActivationTokenModel.id == token.id)
        result = await self.session.execute(stmt)
        db_token = result.scalar_one_or_none()

        if db_token:
            # Actualizar
            db_token.is_used = token.is_used
            db_token.used_at = token.used_at
        else:
            # Crear nuevo
            db_token = ActivationTokenModel(
                id=uuid.uuid4() if not token.id else token.id,
                token=token.token,
                user_id=token.user_id,
                employee_id=token.employee_id,
                created_at=token.created_at,
                expires_at=token.expires_at,
                used_at=token.used_at,
                is_used=token.is_used
            )
            self.session.add(db_token)

        await self.session.commit()
        await self.session.refresh(db_token)

        return self._to_domain(db_token)

    async def find_by_token(self, token: str) -> Optional[ActivationToken]:
        """Busca un token por su valor"""
        stmt = select(ActivationTokenModel).where(ActivationTokenModel.token == token)
        result = await self.session.execute(stmt)
        db_token = result.scalar_one_or_none()

        return self._to_domain(db_token) if db_token else None

    async def find_by_user_id(self, user_id: str) -> Optional[ActivationToken]:
        """Busca tokens de un usuario específico"""
        stmt = select(ActivationTokenModel).where(
            ActivationTokenModel.user_id == user_id
        ).order_by(ActivationTokenModel.created_at.desc())
        result = await self.session.execute(stmt)
        db_token = result.scalar_one_or_none()

        return self._to_domain(db_token) if db_token else None

    async def invalidate_user_tokens(self, user_id: str) -> None:
        """Invalida todos los tokens de un usuario"""
        stmt = select(ActivationTokenModel).where(
            ActivationTokenModel.user_id == user_id,
            ActivationTokenModel.is_used == False
        )
        result = await self.session.execute(stmt)
        tokens = result.scalars().all()

        for token in tokens:
            token.is_used = True
            token.used_at = datetime.now(timezone.utc)

        await self.session.commit()

    def _to_domain(self, db_token: ActivationTokenModel) -> ActivationToken:
        """Convierte modelo de DB a entidad de dominio"""
        return ActivationToken(
            id=str(db_token.id),
            token=db_token.token,
            user_id=str(db_token.user_id),
            employee_id=db_token.employee_id,
            created_at=db_token.created_at,
            expires_at=db_token.expires_at,
            used_at=db_token.used_at,
            is_used=db_token.is_used
        )