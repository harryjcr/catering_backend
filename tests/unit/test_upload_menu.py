import pytest
import base64
import sys
import os
from unittest.mock import AsyncMock

# Agregar path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.menu.application.use_cases.upload_monthly_menu import (
    UploadMonthlyMenuUseCase,
    MonthlyMenu,
    MenuDay
)


class TestUploadMonthlyMenuUseCase:

    @pytest.fixture
    def mock_dependencies(self):
        return {
            'monthly_repo': AsyncMock(),
            'menu_day_repo': AsyncMock(),
            'holiday_service': AsyncMock(),
            'nutrition_validator': AsyncMock()
        }

    @pytest.fixture
    def use_case(self, mock_dependencies):
        return UploadMonthlyMenuUseCase(**mock_dependencies)

    @pytest.fixture
    def sample_csv_base64(self):
        csv_content = """date,breakfast,lunch,dinner
2024-01-15,Cereal,Chicken,Salad
2024-01-16,Toast,Hamburger,Pizza"""
        return base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')

    @pytest.mark.asyncio
    async def test_successful_csv_upload(self, use_case, mock_dependencies, sample_csv_base64):
        # Configurar mocks
        mock_dependencies['monthly_repo'].find_by_year_month.return_value = None
        mock_dependencies['monthly_repo'].upsert.return_value = MonthlyMenu(
            id="test-id", year=2024, month=1, source_filename="test.csv"
        )
        mock_dependencies['holiday_service'].is_holiday.return_value = False

        # Ejecutar
        result = await use_case.execute(
            year=2024, month=1,
            filename="test.csv",
            file_base64=sample_csv_base64
        )

        # Verificar
        assert result["status"] == "ok"
        mock_dependencies['monthly_repo'].upsert.assert_called_once()
        mock_dependencies['menu_day_repo'].bulk_replace.assert_called_once()

    @pytest.mark.asyncio
    async def test_conflict_detection(self, use_case, mock_dependencies, sample_csv_base64):
        # Simular menú existente
        existing_menu = MonthlyMenu(id="existing", year=2024, month=1, source_filename="old.csv")
        mock_dependencies['monthly_repo'].find_by_year_month.return_value = existing_menu

        result = await use_case.execute(2024, 1, "test.csv", sample_csv_base64)

        assert result["status"] == "conflict"
        mock_dependencies['monthly_repo'].upsert.assert_not_called()