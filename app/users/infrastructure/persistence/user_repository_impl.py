from typing import Optional
from datetime import datetime, timezone
from app.users.domain.user import User, UserStatus
from app.users.domain.user_role import UserRole
from app.users.application.ports.user_repository import UserRepository

# OPCIÓN 1: PostgreSQL con SQLAlchemy
import sqlalchemy as sa
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.shared.database.connection import Base

class UserModel(Base):
    """Modelo SQLAlchemy para PostgreSQL"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    personal_email = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)

    full_name = Column(String(255), nullable=False)
    dni = Column(String(20), nullable=False)
    phone = Column(String(20), nullable=True)
    address = Column(String(500), nullable=True)

    data_processing_consent = Column(Boolean, default=False)
    data_processing_consent_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)

    previous_passwords = Column(JSON, default=list)  # Array de hashes


class PostgreSQLUserRepository(UserRepository):
    """Implementación del repositorio de usuarios para PostgreSQL"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, user: User) -> User:
        """Guarda o actualiza un usuario"""
        # Buscar si existe
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self.session.execute(stmt)
        db_user = result.scalar_one_or_none()

        if db_user:
            # Actualizar
            db_user.employee_id = user.employee_id
            db_user.email = user.email
            db_user.personal_email = user.personal_email
            db_user.password_hash = user.password_hash
            db_user.role = user.role.value
            db_user.status = user.status.value
            db_user.full_name = user.full_name
            db_user.dni = user.dni
            db_user.phone = user.phone
            db_user.address = user.address
            db_user.data_processing_consent = user.data_processing_consent
            db_user.data_processing_consent_date = user.data_processing_consent_date
            db_user.updated_at = datetime.now(timezone.utc)
            db_user.activated_at = user.activated_at
            db_user.previous_passwords = user.previous_passwords
        else:
            # Crear nuevo
            db_user = UserModel(
                id=uuid.uuid4() if not user.id else user.id,
                employee_id=user.employee_id,
                email=user.email,
                personal_email=user.personal_email,
                password_hash=user.password_hash,
                role=user.role.value,
                status=user.status.value,
                full_name=user.full_name,
                dni=user.dni,
                phone=user.phone,
                address=user.address,
                data_processing_consent=user.data_processing_consent,
                data_processing_consent_date=user.data_processing_consent_date,
                created_at=user.created_at,
                created_by=user.created_by,
                activated_at=user.activated_at,
                previous_passwords=user.previous_passwords
            )
            self.session.add(db_user)

        await self.session.commit()
        await self.session.refresh(db_user)

        return self._to_domain(db_user)

    async def find_by_id(self, user_id: str) -> Optional[User]:
        """Busca un usuario por ID"""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        db_user = result.scalar_one_or_none()

        return self._to_domain(db_user) if db_user else None

    async def find_by_email(self, email: str) -> Optional[User]:
        """Busca un usuario por email"""
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self.session.execute(stmt)
        db_user = result.scalar_one_or_none()

        return self._to_domain(db_user) if db_user else None

    async def find_by_employee_id(self, employee_id: str) -> Optional[User]:
        """Busca un usuario por employee_id"""
        stmt = select(UserModel).where(UserModel.employee_id == employee_id)
        result = await self.session.execute(stmt)
        db_user = result.scalar_one_or_none()

        return self._to_domain(db_user) if db_user else None

    async def exists_by_email(self, email: str) -> bool:
        """Verifica si existe un usuario con ese email"""
        stmt = select(UserModel.id).where(UserModel.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def exists_by_employee_id(self, employee_id: str) -> bool:
        """Verifica si existe un usuario con ese employee_id"""
        stmt = select(UserModel.id).where(UserModel.employee_id == employee_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    def _to_domain(self, db_user: UserModel) -> User:
        """Convierte modelo de DB a entidad de dominio"""
        return User(
            id=str(db_user.id),
            employee_id=db_user.employee_id,
            email=db_user.email,
            personal_email=db_user.personal_email,
            password_hash=db_user.password_hash,
            role=UserRole(db_user.role),
            status=UserStatus(db_user.status),
            full_name=db_user.full_name,
            dni=db_user.dni,
            phone=db_user.phone,
            address=db_user.address,
            data_processing_consent=db_user.data_processing_consent,
            data_processing_consent_date=db_user.data_processing_consent_date,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
            created_by=str(db_user.created_by) if db_user.created_by else None,
            activated_at=db_user.activated_at,
            previous_passwords=db_user.previous_passwords or []
        )
