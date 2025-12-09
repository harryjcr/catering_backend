import pytest
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.menu.application.use_cases.upload_monthly_menu import (
    _build_header_map,
    _parse_date_flex,
    _all_empty,
    _missing_required
)

class TestMenuParserUnits:
    """Pruebas unitarias de las funciones helper del parser"""

    def test_build_header_map_spanish(self):
        headers = ["fecha", "desayuno", "almuerzo", "cena"]
        result = _build_header_map(headers)
        expected = {
            "date": "fecha",
            "breakfast": "desayuno",
            "lunch": "almuerzo",
            "dinner": "cena"
        }
        assert result == expected

    def test_build_header_map_english(self):
        headers = ["date", "breakfast", "lunch", "dinner"]
        result = _build_header_map(headers)
        expected = {
            "date": "date",
            "breakfast": "breakfast",
            "lunch": "lunch",
            "dinner": "dinner"
        }
        assert result == expected

    def test_parse_date_iso_format(self):
        assert _parse_date_flex("2024-01-15") == date(2024, 1, 15)

    def test_parse_date_dd_mm_yyyy(self):
        assert _parse_date_flex("15/01/2024") == date(2024, 1, 15)


def test_simple():
    """Test simple para verificar que pytest funciona"""
    assert 1 + 1 == 2