"""Implementación del repositorio de horarios"""
from typing import Optional, List
from datetime import date
import uuid

from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, Date, Time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import UUID

from app.shared.database.connection import Base
from app.attendance.domain.work_schedule import WorkSchedule, ShiftType
from app.attendance.application.ports.work_schedule_repository import WorkScheduleRepository

class WorkScheduleModel(Base):
    """Modelo SQLAlchemy para horarios de trabajo"""
    __tablename__ = "work_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    shift_type = Column(String(50), nullable=False)

    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    working_days = Column(JSON, nullable=False)
    late_tolerance_minutes = Column(Integer, nullable=False, default=15)
    break_duration_minutes = Column(Integer, nullable=False, default=30)

    is_active = Column(Boolean, nullable=False, default=True, index=True)
    effective_from = Column(Date, nullable=False)
    effective_until = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    notes = Column(String(500), nullable=True)


class PostgreSQLWorkScheduleRepository(WorkScheduleRepository):
    """Implementación PostgreSQL del repositorio de horarios"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, schedule: WorkSchedule) -> WorkSchedule:
        """Guarda o actualiza un horario"""
        stmt = select(WorkScheduleModel).where(WorkScheduleModel.id == schedule.id)
        result = await self.session.execute(stmt)
        db_schedule = result.scalar_one_or_none()

        if db_schedule:
            self._update_model(db_schedule, schedule)
        else:
            db_schedule = WorkScheduleModel(
                id=uuid.uuid4() if not schedule.id else uuid.UUID(schedule.id),
                **self._to_dict(schedule)
            )
            self.session.add(db_schedule)

        await self.session.commit()
        await self.session.refresh(db_schedule)

        return self._to_domain(db_schedule)

    async def find_by_id(self, schedule_id: str) -> Optional[WorkSchedule]:
        """Busca un horario por ID"""
        stmt = select(WorkScheduleModel).where(WorkScheduleModel.id == schedule_id)
        result = await self.session.execute(stmt)
        db_schedule = result.scalar_one_or_none()

        return self._to_domain(db_schedule) if db_schedule else None

    async def find_active_by_user(self, user_id: str) -> Optional[WorkSchedule]:
        """Obtiene el horario activo de un usuario"""
        stmt = select(WorkScheduleModel).where(
            WorkScheduleModel.user_id == user_id,
            WorkScheduleModel.is_active == True
        ).order_by(WorkScheduleModel.effective_from.desc())

        result = await self.session.execute(stmt)
        db_schedule = result.scalar_one_or_none()

        return self._to_domain(db_schedule) if db_schedule else None

    async def find_by_user_and_date(
        self,
        user_id: str,
        check_date: date
    ) -> Optional[WorkSchedule]:
        """Obtiene el horario válido para un usuario en una fecha específica"""
        stmt = select(WorkScheduleModel).where(
            WorkScheduleModel.user_id == user_id,
            WorkScheduleModel.effective_from <= check_date,
            (WorkScheduleModel.effective_until >= check_date) |
            (WorkScheduleModel.effective_until == None)
        ).order_by(WorkScheduleModel.effective_from.desc())

        result = await self.session.execute(stmt)
        db_schedule = result.scalar_one_or_none()

        return self._to_domain(db_schedule) if db_schedule else None

    async def find_history_by_user(self, user_id: str) -> List[WorkSchedule]:
        """Obtiene el historial de horarios de un usuario"""
        stmt = select(WorkScheduleModel).where(
            WorkScheduleModel.user_id == user_id
        ).order_by(WorkScheduleModel.effective_from.desc())

        result = await self.session.execute(stmt)
        db_schedules = result.scalars().all()

        return [self._to_domain(s) for s in db_schedules]

    def _to_dict(self, schedule: WorkSchedule) -> dict:
        """Convierte entidad de dominio a diccionario"""
        return {
            "user_id": uuid.UUID(schedule.user_id),
            "shift_type": schedule.shift_type.value,
            "start_time": schedule.start_time,
            "end_time": schedule.end_time,
            "working_days": schedule.working_days,
            "late_tolerance_minutes": schedule.late_tolerance_minutes,
            "break_duration_minutes": schedule.break_duration_minutes,
            "is_active": schedule.is_active,
            "effective_from": schedule.effective_from,
            "effective_until": schedule.effective_until,
            "created_at": schedule.created_at,
            "created_by": uuid.UUID(schedule.created_by) if schedule.created_by else None,
            "notes": schedule.notes
        }

    def _update_model(self, model: WorkScheduleModel, schedule: WorkSchedule):
        """Actualiza un modelo existente"""
        data = self._to_dict(schedule)
        for key, value in data.items():
            setattr(model, key, value)

    def _to_domain(self, model: WorkScheduleModel) -> WorkSchedule:
        """Convierte modelo de BD a entidad de dominio"""
        return WorkSchedule(
            id=str(model.id),
            user_id=str(model.user_id),
            shift_type=ShiftType(model.shift_type),
            start_time=model.start_time,
            end_time=model.end_time,
            working_days=model.working_days or [0, 1, 2, 3, 4],
            late_tolerance_minutes=model.late_tolerance_minutes,
            break_duration_minutes=model.break_duration_minutes,
            is_active=model.is_active,
            effective_from=model.effective_from,
            effective_until=model.effective_until,
            created_at=model.created_at,
            created_by=str(model.created_by) if model.created_by else None,
            notes=model.notes
        )