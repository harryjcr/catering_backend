from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from app.shared.config.settings import settings
from app.shared.database.connection import init_db, close_db, get_db_session
from app.shared.graphql.schema import schema
from app.building_blocks.exceptions import AuthenticationException

# USERS
from app.users.infrastructure.persistence.user_repository_impl import PostgreSQLUserRepository
from app.users.infrastructure.persistence.activation_token_repository_impl import PostgreSQLActivationTokenRepository
from app.users.infrastructure.external.email_service import SMTPEmailService
from app.shared.security.auth import JWTAuthService

# ATTENDANCE
from app.attendance.infrastructure.persistence.attendance_repository_impl import PostgreSQLAttendanceRepository
from app.attendance.infrastructure.persistence.work_schedule_repository_impl import (
    PostgreSQLWorkScheduleRepository as AttendanceWorkScheduleRepository
)
from app.attendance.infrastructure.services.simple_holiday_service import SimpleHolidayService

# MENU
from app.menu.infrastructure.persistence.monthly_menu_repository_impl import PostgreSQLMonthlyMenuRepository
from app.menu.infrastructure.persistence.weekly_menu_repository_impl import PostgreSQLWeeklyMenuRepository
from app.menu.infrastructure.persistence.daily_menu_repository_impl import PostgreSQLDailyMenuRepository
from app.menu.infrastructure.persistence.meal_repository_impl import PostgreSQLMealRepository
from app.menu.infrastructure.persistence.meal_component_repository_impl import PostgreSQLMealComponentRepository
from app.menu.infrastructure.persistence.menu_change_repository_impl import PostgreSQLMenuChangeRepository
from app.menu.infrastructure.persistence.component_type_repository_impl import PostgreSQLComponentTypeRepository


# REQUESTS (NO importes el repo de horarios aquí)
from app.requests.infrastructure.persistence.time_off_request_repository_impl import PostgreSQLTimeOffRequestRepository
from app.requests.infrastructure.persistence.vacation_balance_repository_impl import PostgreSQLVacationBalanceRepository
from app.requests.infrastructure.persistence.shift_swap_repository_impl import PostgreSQLShiftSwapRepository
from app.requests.infrastructure.persistence.work_schedule_repository_impl import (
    PostgreSQLWorkScheduleRepository as RequestsWorkScheduleRepository
)

# SANITARY (nuevo)
from app.sanitary.infrastructure.persistence.sanitary_policy_repository_impl import (
    PostgreSQLSanitaryPolicyRepository,
    SanitaryPolicyModel,
)
from app.sanitary.infrastructure.persistence.incident_type_repository_impl import (
    PostgreSQLIncidentTypeRepository,
    IncidentTypeModel,
)
from app.sanitary.infrastructure.persistence.sanitary_review_repository_impl import (
    PostgreSQLSanitaryReviewRepository,
    SanitaryReviewModel,
)
from app.sanitary.infrastructure.persistence.sanitary_company_repository_impl import (
    PostgreSQLSanitaryCompanyRepository,
    SanitaryCompanyModel,
)



@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Iniciando Sistema de Catering...")
    await init_db()
    print("✅ Base de datos inicializada")
    print("📊 GraphQL Playground: http://localhost:8000/graphql")
    yield
    print("👋 Cerrando Sistema de Catering...")
    await close_db()
    print("✅ Conexiones cerradas")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_context(request: Request):
    """
    Context provider for GraphQL using async generator pattern.
    This ensures the session commits after the GraphQL operation completes.
    """
    authorization = request.headers.get("authorization")

    async with get_db_session() as session:
        # Repos existentes
        user_repo = PostgreSQLUserRepository(session)
        token_repo = PostgreSQLActivationTokenRepository(session)
        attendance_repo = PostgreSQLAttendanceRepository(session)

        # Clave: un repo para attendance y otro para requests
        attendance_work_schedule_repo = AttendanceWorkScheduleRepository(session)
        requests_work_schedule_repo = RequestsWorkScheduleRepository(session)

        time_off_repo = PostgreSQLTimeOffRequestRepository(session)
        vacation_balance_repo = PostgreSQLVacationBalanceRepository(session)
        swap_repo = PostgreSQLShiftSwapRepository(session)

        # Menú normalizado (monthly -> weekly -> daily -> meals -> components)
        monthly_menu_repo = PostgreSQLMonthlyMenuRepository(session)
        weekly_menu_repo = PostgreSQLWeeklyMenuRepository(session)
        daily_menu_repo = PostgreSQLDailyMenuRepository(session)
        meal_repo = PostgreSQLMealRepository(session)
        meal_component_repo = PostgreSQLMealComponentRepository(session)
        menu_change_repo = PostgreSQLMenuChangeRepository(session)
        component_type_repo = PostgreSQLComponentTypeRepository(session)

        # Sanidad (módulo de políticas, incidencias y revisiones)
        sanitary_policy_repo = PostgreSQLSanitaryPolicyRepository(session)
        incident_type_repo = PostgreSQLIncidentTypeRepository(session)
        sanitary_review_repo = PostgreSQLSanitaryReviewRepository(session)
        sanitary_company_repo = PostgreSQLSanitaryCompanyRepository(session)

        email_service = SMTPEmailService(
            smtp_host=settings.SMTP_HOST,
            smtp_port=settings.SMTP_PORT,
            smtp_username=settings.SMTP_USERNAME,
            smtp_password=settings.SMTP_PASSWORD,
            from_email=settings.SMTP_FROM_EMAIL,
            from_name=settings.SMTP_FROM_NAME,
        )

        auth_service = JWTAuthService(
            secret_key=settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
            access_token_expire_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
            refresh_token_expire_days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
        )

        holiday_service = SimpleHolidayService()

        current_user = None
        if authorization:
            try:
                token = authorization.replace("Bearer ", "")
                payload = await auth_service.verify_token(token)
                if payload:
                    user_id = payload.get("sub")
                    current_user = await user_repo.find_by_id(user_id)
            except AuthenticationException:
                pass

        context = {
            "request": request,
            "session": session,
            "settings": settings,

            "user_repository": user_repo,
            "token_repository": token_repo,
            "email_service": email_service,
            "auth_service": auth_service,

            # Attendance
            "attendance_repository": attendance_repo,
            "work_schedule_repository": attendance_work_schedule_repo,
            "holiday_service": holiday_service,

            # Requests
            "time_off_repository": time_off_repo,
            "vacation_balance_repository": vacation_balance_repo,
            "swap_repository": swap_repo,
            "requests_work_schedule_repository": requests_work_schedule_repo,

            # Menú
            "monthly_menu_repository": monthly_menu_repo,
            "weekly_menu_repository": weekly_menu_repo,
            "daily_menu_repository": daily_menu_repo,
            "meal_repository": meal_repo,
            "meal_component_repository": meal_component_repo,
            "menu_change_repository": menu_change_repo,
            "component_type_repository": component_type_repo,

            # Sanidad
            "sanitary_policy_repository": sanitary_policy_repo,
            "incident_type_repository": incident_type_repo,
            "sanitary_review_repository": sanitary_review_repo,
            "sanitary_company_repository": sanitary_company_repo,

            "current_user": current_user,
        }

        # Yield the context and let Strawberry execute the query
        # After yield, the async with block will commit the session
        yield context


graphql_app = GraphQLRouter(
    schema=schema,
    context_getter=get_context,
    graphql_ide="apollo-sandbox" if settings.DEBUG else "graphiql",
)
app.include_router(graphql_app, prefix="/graphql")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/")
async def root():
    return {"message": f"Bienvenido a {settings.APP_NAME}", "version": settings.APP_VERSION, "graphql": "/graphql",
            "docs": "/docs"}


app.mount("/static", StaticFiles(directory="app/users/static"), name="static")


@app.get("/activate")
async def activate_page():
    return FileResponse("app/users/templates/activate.html")


@app.get("/activate/success")
async def activate_success_page():
    return FileResponse("app/users/templates/activate_success.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
