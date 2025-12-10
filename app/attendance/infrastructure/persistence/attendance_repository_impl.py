"""Implementación del repositorio de asistencia con PostgreSQL"""
from typing import Optional, List
from datetime import date, datetime
import uuid

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, JSON, Date, Time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import UUID

from app.shared.database.connection import Base
from app.attendance.domain.attendance import Attendance
from app.attendance.domain.attendance_status import AttendanceStatus, AttendanceType
from app.attendance.domain.geolocation import Geolocation
from app.attendance.domain.break_period import BreakPeriod, BreakStatus
from app.attendance.application.ports.attendance_repository import AttendanceRepository


class AttendanceModel(Base):
    """Modelo SQLAlchemy para asistencia"""
    __tablename__ = "attendances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    # Horarios
    check_in_time = Column(DateTime(timezone=True), nullable=True)
    check_out_time = Column(DateTime(timezone=True), nullable=True)
    scheduled_start_time = Column(Time, nullable=True)  # Viene del WorkSchedule
    scheduled_end_time = Column(Time, nullable=True)

    # Estado
    status = Column(String(50), nullable=False)
    type = Column(String(50), nullable=False)

    # Geolocalización (JSON)
    check_in_location = Column(JSON, nullable=True)
    check_out_location = Column(JSON, nullable=True)
    workplace_location = Column(JSON, nullable=True)
    workplace_radius_meters = Column(Float, nullable=False, default=100.0)

    # Tardanzas
    is_late = Column(Boolean, default=False)
    late_minutes = Column(Integer, default=0)
    late_tolerance_minutes = Column(Integer, default=15, nullable=False)

    # Regularización
    requires_regularization = Column(Boolean, default=False)
    regularization_notes = Column(String(500), nullable=True)
    regularized_by = Column(UUID(as_uuid=True), nullable=True)
    regularized_at = Column(DateTime(timezone=True), nullable=True)

    # Descansos (JSON array)
    break_periods = Column(JSON, nullable=False, default=list)

    # Metadatos
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class PostgreSQLAttendanceRepository(AttendanceRepository):
    """Implementación PostgreSQL del repositorio de asistencia"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, attendance: Attendance) -> Attendance:
        """Guarda o actualiza una asistencia"""
        stmt = select(AttendanceModel).where(AttendanceModel.id == attendance.id)
        result = await self.session.execute(stmt)
        db_attendance = result.scalar_one_or_none()

        if db_attendance:
            # Actualizar
            self._update_model(db_attendance, attendance)
        else:
            # Crear nuevo
            db_attendance = AttendanceModel(
                id=uuid.uuid4() if not attendance.id else uuid.UUID(attendance.id),
                **self._to_dict(attendance)
            )
            self.session.add(db_attendance)

        await self.session.commit()
        await self.session.refresh(db_attendance)

        return self._to_domain(db_attendance)

    async def find_by_id(self, attendance_id: str) -> Optional[Attendance]:
        """Busca una asistencia por ID"""
        stmt = select(AttendanceModel).where(AttendanceModel.id == UUID(attendance_id))
        result = await self.session.execute(stmt)
        db_attendance = result.scalar_one_or_none()

        return self._to_domain(db_attendance) if db_attendance else None

    async def find_by_user_and_date(self, user_id: str, check_date: date) -> Optional[Attendance]:
        """Busca la asistencia de un usuario para una fecha específica"""
        stmt = select(AttendanceModel).where(
            AttendanceModel.user_id == user_id,
            AttendanceModel.date == check_date
        )
        result = await self.session.execute(stmt)
        db_attendance = result.scalar_one_or_none()

        return self._to_domain(db_attendance) if db_attendance else None

    async def find_by_user(self, user_id: str, limit: int = 30) -> List[Attendance]:
        """Obtiene las últimas asistencias de un usuario"""
        stmt = select(AttendanceModel).where(
            AttendanceModel.user_id == user_id
        ).order_by(AttendanceModel.date.desc()).limit(limit)

        result = await self.session.execute(stmt)
        db_attendances = result.scalars().all()

        return [self._to_domain(a) for a in db_attendances]

    async def has_pending_regularization(self, user_id: str) -> bool:
        """Verifica si el usuario tiene asistencias pendientes de regularizar"""
        stmt = select(AttendanceModel.id).where(
            AttendanceModel.user_id == user_id,
            AttendanceModel.requires_regularization == True
        ).limit(1)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    def _to_dict(self, attendance: Attendance) -> dict:
        """Convierte entidad de dominio a diccionario para BD"""
        return {
            "user_id": uuid.UUID(attendance.user_id),
            "date": attendance.date.date(),
            "check_in_time": attendance.check_in_time,
            "check_out_time": attendance.check_out_time,
            "scheduled_start_time": attendance.scheduled_start_time,
            "scheduled_end_time": attendance.scheduled_end_time,
            "status": attendance.status.value,
            "type": attendance.type.value,
            "check_in_location": self._location_to_json(attendance.check_in_location),
            "check_out_location": self._location_to_json(attendance.check_out_location),
            "workplace_location": self._location_to_json(attendance.workplace_location),
            "workplace_radius_meters": attendance.workplace_radius_meters,
            "is_late": attendance.is_late,
            "late_minutes": attendance.late_minutes,
            "late_tolerance_minutes": attendance.late_tolerance_minutes,
            "requires_regularization": attendance.requires_regularization,
            "regularization_notes": attendance.regularization_notes,
            "regularized_by": uuid.UUID(attendance.regularized_by) if attendance.regularized_by else None,
            "regularized_at": attendance.regularized_at,
            "break_periods": self._breaks_to_json(attendance.break_periods),
            "created_at": attendance.created_at,
            "updated_at": attendance.updated_at
        }

    def _update_model(self, model: AttendanceModel, attendance: Attendance):
        """Actualiza un modelo existente"""
        data = self._to_dict(attendance)
        for key, value in data.items():
            setattr(model, key, value)

    def _to_domain(self, model: AttendanceModel) -> Attendance:
        """Convierte modelo de BD a entidad de dominio"""
        return Attendance(
            id=str(model.id),
            user_id=str(model.user_id),
            date=datetime.combine(model.date, datetime.min.time()),
            check_in_time=model.check_in_time,
            check_out_time=model.check_out_time,
            scheduled_start_time=model.scheduled_start_time,
            scheduled_end_time=model.scheduled_end_time,
            status=AttendanceStatus(model.status),
            type=AttendanceType(model.type),
            check_in_location=self._json_to_location(model.check_in_location),
            check_out_location=self._json_to_location(model.check_out_location),
            workplace_location=self._json_to_location(model.workplace_location),
            workplace_radius_meters=model.workplace_radius_meters,
            is_late=model.is_late,
            late_minutes=model.late_minutes,
            late_tolerance_minutes=model.late_tolerance_minutes,
            requires_regularization=model.requires_regularization,
            regularization_notes=model.regularization_notes,
            regularized_by=str(model.regularized_by) if model.regularized_by else None,
            regularized_at=model.regularized_at,
            break_periods=self._json_to_breaks(model.break_periods),
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    @staticmethod
    def _location_to_json(location: Optional[Geolocation]) -> Optional[dict]:
        """Convierte Geolocation a JSON"""
        if not location:
            return None
        return {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "accuracy": location.accuracy
        }

    @staticmethod
    def _json_to_location(data: Optional[dict]) -> Optional[Geolocation]:
        """Convierte JSON a Geolocation"""
        if not data:
            return None
        return Geolocation(
            latitude=data["latitude"],
            longitude=data["longitude"],
            accuracy=data.get("accuracy", 10.0)
        )

    @staticmethod
    def _breaks_to_json(breaks: List[BreakPeriod]) -> list:
        """Convierte lista de BreakPeriod a JSON"""
        return [
            {
                "id": bp.id,
                "start_time": bp.start_time.isoformat() if bp.start_time else None,
                "end_time": bp.end_time.isoformat() if bp.end_time else None,
                "status": bp.status.value,
                "start_location": PostgreSQLAttendanceRepository._location_to_json(bp.start_location),
                "end_location": PostgreSQLAttendanceRepository._location_to_json(bp.end_location),
                "allowed_duration_minutes": bp.allowed_duration_minutes
            }
            for bp in breaks
        ]

    @staticmethod
    def _json_to_breaks(data: list) -> List[BreakPeriod]:
        """Convierte JSON a lista de BreakPeriod"""
        if not data:
            return []

        return [
            BreakPeriod(
                id=bp["id"],
                start_time=datetime.fromisoformat(bp["start_time"]) if bp["start_time"] else None,
                end_time=datetime.fromisoformat(bp["end_time"]) if bp["end_time"] else None,
                status=BreakStatus(bp["status"]),
                start_location=PostgreSQLAttendanceRepository._json_to_location(bp.get("start_location")),
                end_location=PostgreSQLAttendanceRepository._json_to_location(bp.get("end_location")),
                allowed_duration_minutes=bp.get("allowed_duration_minutes", 30)
            )
            for bp in data
        ]