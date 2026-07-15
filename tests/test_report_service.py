"""Tests for secret-free report output."""
from crtnm.application.report_service import ReportService


def test_csv_has_bom_and_table() -> None:
    output = ReportService.to_csv(["Device"], [["Router-1"]])
    assert output.startswith(b"\xef\xbb\xbfDevice")
    assert b"Router-1" in output


def test_xlsx_is_a_zip_container() -> None:
    output = ReportService.to_xlsx(["Device"], [["Router-1"]])
    assert output.startswith(b"PK")
