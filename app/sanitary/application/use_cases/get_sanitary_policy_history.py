from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Any, List
from uuid import UUID
import calendar

from app.sanitary.application.ports.sanitary_policy_repository import (
    SanitaryPolicyRepository,
)
from app.sanitary.application.ports.sanitary_review_repository import (
    SanitaryReviewRepository,
)


def get_last_day_of_month(year: int, month: int) -> date:
    """
    Get the last day of a given month.

    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)

    Returns:
        Date object representing the last day of the month
    """
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def get_last_day_of_next_month(reference_date: date) -> date:
    """
    Get the last day of the month following the reference date.

    Examples:
        - If review done on 2024-01-25, returns 2024-02-29 (last day of February)
        - If review done on 2024-01-31, returns 2024-02-29
        - If review done on 2024-12-15, returns 2025-01-31

    Args:
        reference_date: The date from which to calculate

    Returns:
        Date object representing the last day of the following month
    """
    # Calculate next month
    if reference_date.month == 12:
        next_year = reference_date.year + 1
        next_month = 1
    else:
        next_year = reference_date.year
        next_month = reference_date.month + 1

    return get_last_day_of_month(next_year, next_month)


@dataclass
class GetSanitaryPolicyHistoryCommand:
    """
    Comando para consultar el historial de una política de sanidad.

    Campos alineados con tus pantallas:
      - policy_id    -> política seleccionada (ej. 'Control de plagas')
      - months_back  -> periodo a mostrar en el historial:
                        6, 12, 24 meses (6m, 1 año, 2 años)
    """

    policy_id: UUID
    months_back: int  # 6, 12, 24, etc.


class GetSanitaryPolicyHistoryUseCase:
    """
    Caso de uso para obtener la información que se ve en la pantalla de detalle
    de una política:

      - Datos básicos de la política.
      - Historial de revisiones en un periodo (6m, 1 año, 2 años).
      - Fecha de la última revisión.
      - Próxima revisión (= último día del mes siguiente a la última revisión).

    Lógica de próxima revisión:
      - Siempre se programa para el último día del mes siguiente.
      - Ejemplo: Si la revisión se hace el 25/01/2024, la próxima será el 29/02/2024.
      - Si no hay revisiones previas, se programa para el último día del mes actual.

    *No añadimos ningún campo nuevo a la BD; todo se calcula a partir de las revisiones.*
    """

    def __init__(
        self,
        policy_repo: SanitaryPolicyRepository,
        review_repo: SanitaryReviewRepository,
    ) -> None:
        self._policy_repo = policy_repo
        self._review_repo = review_repo

    async def execute(self, cmd: GetSanitaryPolicyHistoryCommand) -> Dict[str, Any]:
        # 1) Validar que la política exista
        policy = await self._policy_repo.get_by_id(cmd.policy_id)
        if not policy:
            return {
                "success": False,
                "message": "La política de sanidad seleccionada no existe.",
                "policy": None,
                "history": [],
                "last_review_date": None,
                "next_review_date": None,
            }

        # 2) Calcular rango de fechas del historial
        today = date.today()

        # months_back lo convertimos a días aproximados (30 días por mes),
        # suficiente para el filtro de historial 6m, 1 año, 2 años.
        days_back = cmd.months_back * 30
        start_date = today - timedelta(days=days_back)
        end_date = today

        # 3) Obtener historial en ese rango
        reviews = await self._review_repo.list_by_policy_and_period(
            policy_id=cmd.policy_id,
            start_date=start_date,
            end_date=end_date,
        )

        # 4) Obtener última revisión (para calcular próxima)
        last_review = await self._review_repo.get_last_by_policy(cmd.policy_id)
        if last_review:
            last_review_date = last_review.date
            # Next review is always the last day of the following month
            next_review_date = get_last_day_of_next_month(last_review_date)
        else:
            # If no reviews exist, default to last day of current month
            last_review_date = None
            today = date.today()
            next_review_date = get_last_day_of_month(today.year, today.month)

        # 5) Mapear historial a un formato simple para la UI
        history: List[Dict[str, Any]] = []
        for r in reviews:
            history.append(
                {
                    "id": str(r.id),
                    "policy_id": str(r.policy_id),
                    "user_id": str(r.user_id),
                    "date": r.date.isoformat(),
                    "is_conform": r.is_conform,
                    "observation": r.observation,
                    "incident_type_id": str(r.incident_type_id) if r.incident_type_id else None,
                    "company_id": str(r.company_id) if r.company_id else None,
                }
            )

        # 6) Armar respuesta
        return {
            "success": True,
            "message": "Historial de la política obtenido correctamente.",
            "policy": {
                "id": str(policy.id),
                "name": policy.name,
                "description": policy.description,
                "is_active": policy.is_active,
            },
            "history": history,
            "last_review_date": last_review_date.isoformat() if last_review_date else None,
            "next_review_date": next_review_date.isoformat() if next_review_date else None,
        }
