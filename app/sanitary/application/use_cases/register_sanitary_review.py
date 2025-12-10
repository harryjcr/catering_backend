from dataclasses import dataclass
from datetime import date
from typing import Optional, Dict, Any
from uuid import UUID

from app.sanitary.application.ports.sanitary_policy_repository import (
    SanitaryPolicyRepository,
)
from app.sanitary.application.ports.incident_type_repository import (
    IncidentTypeRepository,
)
from app.sanitary.application.ports.sanitary_review_repository import (
    SanitaryReviewRepository,
)
from app.sanitary.application.ports.sanitary_company_repository import (
    SanitaryCompanyRepository,
)
from app.sanitary.domain.sanitary_review import SanitaryReview


@dataclass
class RegisterSanitaryReviewCommand:
    """
    Comando para registrar una revisión de sanidad.

    Campos alineados con tu E-R y las pantallas:
      - policy_id           -> política que se está evaluando
      - date                -> fecha de la revisión (la que se ve arriba en la UI)
      - is_conform          -> resultado (Conforme / Inconforme)
      - observation         -> comentario general
      - incident_type_id    -> tipo de incidencia (solo si es inconforme)
      - company_id          -> empresa a contactar (solo si es inconforme)
      - user_id             -> usuario (nutricionista) que realiza la revisión
    """

    policy_id: UUID
    date: date
    is_conform: bool
    user_id: UUID

    observation: Optional[str] = None
    incident_type_id: Optional[UUID] = None
    company_id: Optional[UUID] = None


class RegisterSanitaryReviewUseCase:
    """
    Caso de uso para registrar una revisión de sanidad.

    Reglas de negocio (según tu aclaración + interfaces):
      - La política debe existir.
      - Si is_conform = True:
          * NO se exige incident_type_id ni company_id.
      - Si is_conform = False:
          * incident_type_id es OBLIGATORIO.
          * company_id es OBLIGATORIO.
          * El tipo de incidencia debe existir.
          * El tipo de incidencia debe pertenecer a la MISMA política.
          * La empresa debe existir (empresa especializada a contactar).
    """

    def __init__(
        self,
        policy_repo: SanitaryPolicyRepository,
        incident_type_repo: IncidentTypeRepository,
        review_repo: SanitaryReviewRepository,
        company_repo: SanitaryCompanyRepository,
    ) -> None:
        self._policy_repo = policy_repo
        self._incident_type_repo = incident_type_repo
        self._review_repo = review_repo
        self._company_repo = company_repo

    async def execute(self, cmd: RegisterSanitaryReviewCommand) -> Dict[str, Any]:
        # 1) Validar que la política exista
        policy = await self._policy_repo.get_by_id(cmd.policy_id)
        if not policy:
            return {
                "success": False,
                "message": "La política de sanidad seleccionada no existe.",
                "review": None,
            }

        # 2) Validar según resultado
        if cmd.is_conform:
            # Conforme: no exigimos tipo de incidencia ni empresa
            review = SanitaryReview.create_conform(
                policy_id=cmd.policy_id,
                user_id=cmd.user_id,
                date_value=cmd.date,
                observation=cmd.observation,
            )
        else:
            # Inconforme: tipo de incidencia y empresa SON obligatorios
            if cmd.incident_type_id is None:
                return {
                    "success": False,
                    "message": "Debe seleccionar un tipo de incidencia para una revisión inconforme.",
                    "review": None,
                }

            if cmd.company_id is None:
                return {
                    "success": False,
                    "message": "Debe seleccionar una empresa a contactar para una revisión inconforme.",
                    "review": None,
                }

            # 2.1) Validar que el tipo de incidencia exista
            incident_type = await self._incident_type_repo.get_by_id(cmd.incident_type_id)
            if not incident_type:
                return {
                    "success": False,
                    "message": "El tipo de incidencia seleccionado no existe.",
                    "review": None,
                }

            # 2.2) Validar que el tipo de incidencia pertenezca a la misma política
            if incident_type.policy_id != cmd.policy_id:
                return {
                    "success": False,
                    "message": f"El tipo de incidencia '{incident_type.name}' (policy_id: {incident_type.policy_id}) no pertenece a la política seleccionada (policy_id: {cmd.policy_id}).",
                    "review": None,
                }

            # 2.3) Validar que la empresa exista
            company = await self._company_repo.get_by_id(cmd.company_id)
            if not company:
                return {
                    "success": False,
                    "message": "La empresa seleccionada no existe.",
                    "review": None,
                }

            # 2.4) Crear revisión inconforme
            review = SanitaryReview.create_non_conform(
                policy_id=cmd.policy_id,
                user_id=cmd.user_id,
                date_value=cmd.date,
                incident_type_id=cmd.incident_type_id,
                company_id=cmd.company_id,
                observation=cmd.observation,
            )

        # 3) Guardar la revisión
        saved = await self._review_repo.save(review)

        # 4) Respuesta estándar (igual estilo que swaps / otros módulos)
        return {
            "success": True,
            "message": "Revisión de sanidad registrada correctamente.",
            "review": {
                "id": str(saved.id),
                "policy_id": str(saved.policy_id),
                "user_id": str(saved.user_id),
                "date": saved.date.isoformat(),
                "is_conform": saved.is_conform,
                "observation": saved.observation,
                "incident_type_id": str(saved.incident_type_id) if saved.incident_type_id else None,
                "company_id": str(saved.company_id) if saved.company_id else None,
            },
        }
