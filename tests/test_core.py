"""Smoke + correctness tests for the SLA core, run against the real Fresh export."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sla_core import load_standardised, kpi, by_company, list_companies, list_months  # noqa: E402
from sla_core.companies import company_for_email  # noqa: E402
from sla_core.sla_engine import derive_sla  # noqa: E402
import pandas as pd  # noqa: E402

EXPORT = Path("/Users/vaughan.fawcett/Downloads/Export Example_May.csv")


def test_company_mapping():
    assert company_for_email("a.b@mitie.com") == "Mitie"
    assert company_for_email("x@astrazeneca.com") == "AstraZeneca"
    assert company_for_email("no-reply@tmc.co.uk") == "TMC (Internal)"
    assert company_for_email("someone@gmail.com") == "Personal / Unknown"
    assert company_for_email("") == "Personal / Unknown"
    assert company_for_email("j@brand-new-co.co.uk") == "Brand New Co"  # prettified fallback


def test_sla_engine_rule():
    df = pd.DataFrame({
        "first_response_status": ["Within SLA", "", "SLA Violated", ""],
        "resolution_status": ["Within SLA", "Within SLA", "Within SLA", ""],
        "every_response_status": ["", "", "", "SLA Violated"],
    })
    out = derive_sla(df)
    assert out["sla_within_flag"].tolist() == ["Y", "Y", "N", "N"]
    assert out["sla_status"].tolist() == [
        "Within SLA", "Within SLA", "Outside SLA", "Outside SLA"]


def test_iso_and_dayfirst_dates_both_parse():
    """Freshdesk ISO (YYYY-MM-DD) and cleaned DD/MM/YYYY must both map to the
    correct month — ISO must NOT be day-first parsed (regression guard)."""
    from sla_core.ingest import _parse_datetimes
    iso = _parse_datetimes(pd.Series(["2026-05-13 05:30:36", "2026-05-01 02:09:49"]))
    assert iso.dt.strftime("%Y-%m").tolist() == ["2026-05", "2026-05"]  # not 2026-01 / dropped
    dayfirst = _parse_datetimes(pd.Series(["13/05/2026 05:30", "01/05/2026 02:09"]))
    assert dayfirst.dt.strftime("%Y-%m").tolist() == ["2026-05", "2026-05"]
    assert _parse_datetimes(pd.Series([""])).isna().all()  # blank -> NaT, no crash


def test_ingest_real_export():
    res = load_standardised(EXPORT.read_bytes(), EXPORT.name)
    assert res.row_count == 6941
    # Validated separately: exactly 148 breaches -> 6793 within.
    overall = kpi(res.df)
    assert overall["total_tickets"] == 6941
    assert overall["within_sla"] == 6793
    assert overall["outside_sla"] == 148
    assert overall["sla_percentage"] == round(100 * 6793 / 6941, 2)

    # Brief's example contract shape.
    assert set(overall) == {"company", "month", "total_tickets",
                            "within_sla", "outside_sla", "sla_percentage"}

    # Filtering works.
    assert "Mitie" in list_companies(res.df)
    assert "2026-05" in list_months(res.df)
    mitie_may = kpi(res.df, "Mitie", "2026-05")
    assert mitie_may["total_tickets"] > 0
    assert mitie_may["within_sla"] + mitie_may["outside_sla"] == mitie_may["total_tickets"]

    bc = by_company(res.df, month="2026-05")
    assert (bc["Within SLA"] + bc["Outside SLA"] == bc["Total"]).all()


if __name__ == "__main__":
    test_company_mapping()
    test_sla_engine_rule()
    test_iso_and_dayfirst_dates_both_parse()
    test_ingest_real_export()
    print("All tests passed.")
