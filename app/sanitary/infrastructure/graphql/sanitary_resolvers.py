import datetime
from typing import List
from uuid import UUID

import strawberry
from strawberry.types import Info

from app.sanitary.application.use_cases.list_sanitary_policies import (
    ListSanitaryPoliciesUseCase,
    ListSanitaryPoliciesCommand,
)
from app.sanitary.application.use_cases.get_sanitary_policy_history import (
    GetSanitaryPolicyHistoryUseCase,
    GetSanitaryPolicyHistoryCommand,
)
from app.sanitary.application.use_cases.register_sanitary_review import (
    RegisterSanitaryReviewUseCase,
    RegisterSanitaryReviewCommand,
)

from app.sanitary.infrastructure.graphql.sanitary_types import (
    SanitaryPolicyType,
    SanitaryCompanyType,
    IncidentTypeType,
    SanitaryReviewType,
    RegisterSanitaryReviewInput,
    SanitaryPolicyHistoryFilterInput,
    SanitaryPoliciesResponse,
    SanitaryPolicyHistoryResponse,
    RegisterSanitaryReviewResponse,
)


# =========================
# Helpers de mapeo
# =========================

def _map_policy_dict_to_type(p: dict) -> SanitaryPolicyType:
    return SanitaryPolicyType(
        id=strawberry.ID(p["id"]),
        name=p["name"],
        description=p.get("description"),
        is_active=p["is_active"],
    )


def _map_review_dict_to_type(r: dict) -> SanitaryReviewType:
    return SanitaryReviewType(
        id=strawberry.ID(r["id"]),
        policy_id=strawberry.ID(r["policy_id"]),
        user_id=strawberry.ID(r["user_id"]),
        date=datetime.date.fromisoformat(r["date"]),
        is_conform=bool(r["is_conform"]),
        observation=r.get("observation"),
        incident_type_id=strawberry.ID(r["incident_type_id"]) if r.get("incident_type_id") else None,
        company_id=strawberry.ID(r["company_id"]) if r.get("company_id") else None,
    )


# =========================
# Queries
# =========================

@strawberry.type
class SanitaryQueries:
    """
    Root de queries relacionadas con el módulo de sanidad.
    """

    @strawberry.field
    async def sanitary_policies(self, info: Info) -> SanitaryPoliciesResponse:
        """
        Lista las políticas de sanidad activas (pantalla de listado).
        """
        policy_repo = info.context["sanitary_policy_repository"]

        uc = ListSanitaryPoliciesUseCase(policy_repo)
        result = await uc.execute(ListSanitaryPoliciesCommand(include_inactive=False))

        policies = [_map_policy_dict_to_type(p) for p in result["policies"]]

        return SanitaryPoliciesResponse(
            success=result["success"],
            message=result["message"],
            policies=policies,
        )

    @strawberry.field
    async def sanitary_policy_history(
        self,
        info: Info,
        filter: SanitaryPolicyHistoryFilterInput,
    ) -> SanitaryPolicyHistoryResponse:
        """
        Historial de una política de sanidad, con:
          - datos básicos de la política
          - lista de revisiones en el periodo (6m, 1 año, 2 años)
          - última fecha de revisión
          - próxima revisión (= última + 30 días)
        """
        policy_repo = info.context["sanitary_policy_repository"]
        review_repo = info.context["sanitary_review_repository"]

        uc = GetSanitaryPolicyHistoryUseCase(policy_repo, review_repo)

        cmd = GetSanitaryPolicyHistoryCommand(
            policy_id=filter.policy_id,
            months_back=filter.months_back,
        )
        result = await uc.execute(cmd)

        if not result["success"] or result["policy"] is None:
            return SanitaryPolicyHistoryResponse(
                success=result["success"],
                message=result["message"],
                policy=None,
                history=[],
                last_review_date=None,
                next_review_date=None,
            )

        policy_type = _map_policy_dict_to_type(result["policy"])
        history_types: List[SanitaryReviewType] = [
            _map_review_dict_to_type(r) for r in result["history"]
        ]

        last_review_date = (
            datetime.date.fromisoformat(result["last_review_date"])
            if result["last_review_date"]
            else None
        )
        next_review_date = (
            datetime.date.fromisoformat(result["next_review_date"])
            if result["next_review_date"]
            else None
        )

        return SanitaryPolicyHistoryResponse(
            success=True,
            message=result["message"],
            policy=policy_type,
            history=history_types,
            last_review_date=last_review_date,
            next_review_date=next_review_date,
        )

    @strawberry.field
    async def sanitary_incident_types_by_policy(
        self,
        info: Info,
        policy_id: strawberry.ID,
    ) -> List[IncidentTypeType]:
        """
        Lista los tipos de incidencia vinculados a una política,
        para poblar el combo 'Tipo de incidencia' cuando se marca INCONFORME.
        """
        repo = info.context["incident_type_repository"]
        incident_types = await repo.list_by_policy(policy_id, only_active=True)

        return [
            IncidentTypeType(
                id=strawberry.ID(str(it.id)),
                policy_id=strawberry.ID(str(it.policy_id)),
                name=it.name,
                description=it.description,
                is_active=it.is_active,
            )
            for it in incident_types
        ]

    @strawberry.field
    async def sanitary_companies(self, info: Info) -> List[SanitaryCompanyType]:
        """
        Lista las empresas especializadas de sanidad,
        para poblar el combo 'Empresa a contactar' en caso INCONFORME.
        """
        repo = info.context["sanitary_company_repository"]
        companies = await repo.list_all()

        return [
            SanitaryCompanyType(
                id=strawberry.ID(str(c.id)),
                business_name=c.business_name,
                ruc=c.ruc,
                phone=c.phone,
                email=c.email,
            )
            for c in companies
        ]


# =========================
# Mutations
# =========================

@strawberry.type
class SanitaryMutations:
    """
    Root de mutations relacionadas con el módulo de sanidad.
    """

    @strawberry.mutation
    async def register_sanitary_review(
        self,
        info: Info,
        input: RegisterSanitaryReviewInput,
    ) -> RegisterSanitaryReviewResponse:
        """
        Registra una revisión de sanidad (Conforme / Inconforme),
        tal como se ve en las pantallas del nutricionista.
        """
        policy_repo = info.context["sanitary_policy_repository"]
        incident_type_repo = info.context["incident_type_repository"]
        review_repo = info.context["sanitary_review_repository"]
        company_repo = info.context["sanitary_company_repository"]

        current_user = info.context["current_user"]
        if current_user is None:
            return RegisterSanitaryReviewResponse(
                success=False,
                message="Usuario no autenticado.",
                review=None,
            )

        uc = RegisterSanitaryReviewUseCase(
            policy_repo=policy_repo,
            incident_type_repo=incident_type_repo,
            review_repo=review_repo,
            company_repo=company_repo,
        )

        cmd = RegisterSanitaryReviewCommand(
            policy_id=UUID(input.policy_id),
            date=input.date,
            is_conform=input.is_conform,
            observation=input.observation,
            incident_type_id=UUID(input.incident_type_id) if input.incident_type_id else None,
            company_id=UUID(input.company_id) if input.company_id else None,
            user_id=current_user.id,
        )

        result = await uc.execute(cmd)

        if not result["success"] or result["review"] is None:
            return RegisterSanitaryReviewResponse(
                success=result["success"],
                message=result["message"],
                review=None,
            )

        review_type = _map_review_dict_to_type(result["review"])

        return RegisterSanitaryReviewResponse(
            success=True,
            message=result["message"],
            review=review_type,
        )
