"""Gate: registration must not embed harness fixture coordinates."""

from __future__ import annotations

from services import registration_service
from tests.support.repo import REPO_ROOT


def test_registration_service_has_no_fixture_coordinate_table():
    source = (REPO_ROOT / "services" / "registration_service.py").read_text(
        encoding="utf-8"
    )
    assert "_KNOWN_STREET_HAAT" not in source
    # Exact former fixture literals must not reappear in production code.
    assert "38.882162" not in source
    assert "-77.113755" not in source


def test_cat_a_haat_check_is_provider_noop_for_arbitrary_coordinates():
    # Use non-fixture coordinates; HAAT remains unevaluated without a terrain provider.
    assert (
        registration_service._cat_a_outdoor_haat_exceeds_limit(
            {
                "latitude": 10.0,
                "longitude": 20.0,
                "height": 1.0,
                "heightType": "AGL",
            }
        )
        is False
    )
