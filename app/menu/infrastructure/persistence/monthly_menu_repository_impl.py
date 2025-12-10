# imports
import uuid
import sqlalchemy as sa
from typing import Optional, List
from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID as PG_UUID, insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import Column, Integer, String, DateTime, text

from app.shared.database.connection import Base

from app.menu.application.ports.monthly_menu_repository import MonthlyMenuRepository
from app.menu.domain.monthly_menu import MonthlyMenu
from app.menu.domain.menu_enums import MenuStatus


class MonthlyMenuModel(Base):
    __tablename__ = "monthly_menus"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)
    status = Column(String(20), nullable=False, default=MenuStatus.DRAFT.value)
    source_filename = Column(String(255), nullable=True)
    created_by = Column(PG_UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.UniqueConstraint("year", "month", name="uq_monthly_menus_year_month"),
    )

class PostgreSQLMonthlyMenuRepository(MonthlyMenuRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.session_factory = async_sessionmaker(bind=session.bind, expire_on_commit=False)

    def _to_domain(self, m: MonthlyMenuModel) -> MonthlyMenu:
        return MonthlyMenu(
            id=str(m.id),
            year=m.year,
            month=m.month,
            status=MenuStatus(m.status),
            source_filename=m.source_filename,
            created_by=str(m.created_by) if m.created_by else None,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    async def upsert(self, m: MonthlyMenu) -> MonthlyMenu:
        async with self.session_factory() as session:
            async with session.begin():
                stmt = pg_insert(MonthlyMenuModel).values(
                    id=m.id,                    # UUID
                    year=m.year,                # int
                    month=m.month,              # int
                    status=m.status.value,      # str
                    source_filename=m.source_filename,
                    created_at=m.created_at,
                    updated_at=m.updated_at,
                )

                stmt = stmt.on_conflict_do_update(
                    index_elements=[MonthlyMenuModel.year, MonthlyMenuModel.month],
                    set_={
                        "status": m.status.value,
                        "source_filename": stmt.excluded.source_filename,
                        "updated_at": text("now()"),
                    },
                ).returning(
                    MonthlyMenuModel.id,
                    MonthlyMenuModel.year,
                    MonthlyMenuModel.month,
                    MonthlyMenuModel.status,
                    MonthlyMenuModel.source_filename,
                    MonthlyMenuModel.created_at,
                    MonthlyMenuModel.updated_at,
                )

                row = (await session.execute(stmt)).one()
            # fuera del begin, mapear a dominio
            return MonthlyMenu(
                id=row.id,
                year=row.year,
                month=row.month,
                status=MenuStatus(row.status),
                source_filename=row.source_filename,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    async def find_by_year_month(self, year: int, month: int) -> MonthlyMenu | None:
        async with self.session_factory() as session:
            q = select(MonthlyMenuModel).where(
                (MonthlyMenuModel.year == year) & (MonthlyMenuModel.month == month)
            )
            r = await session.execute(q)
            mm = r.scalar_one_or_none()
            if not mm:
                return None
            return MonthlyMenu(
                id=mm.id,
                year=mm.year,
                month=mm.month,
                status=MenuStatus(mm.status),
                source_filename=mm.source_filename,
                created_at=mm.created_at,
                updated_at=mm.updated_at,
            )

    async def find_by_id(self, menu_id: str) -> Optional[MonthlyMenu]:
        stmt = select(MonthlyMenuModel).where(MonthlyMenuModel.id == uuid.UUID(menu_id)).limit(1)
        r = await self.session.execute(stmt)
        m = r.scalar_one_or_none()
        return self._to_domain(m) if m else None

    async def list_recent(self, limit: int = 12) -> List[MonthlyMenu]:
        stmt = select(MonthlyMenuModel).order_by(MonthlyMenuModel.created_at.desc()).limit(limit)
        r = await self.session.execute(stmt)
        rows = r.scalars().all()
        return [self._to_domain(m) for m in rows]
