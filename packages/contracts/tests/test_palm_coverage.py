from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from pandit_contracts.palm_coverage import (
    CoverageRecord,
    CoverageStatus,
    PalmSourceCoverage,
)


def _rec(**overrides: Any) -> CoverageRecord:
    fields: dict[str, Any] = {
        "source_id": "SRC-HERONALLEN-CHEIROSOPHY",
        "profile_id": "PALM_HA_MAP_LINES_384_393",
        "methodology_profile": "PALM_WESTERN",
        "location": "para. 384, p. 190",
        "concept_id": "PALM_LINE.LIFE",
        "status": CoverageStatus.SUPPORTED,
        "reading_level": "PAGE_IMAGE_LEVEL",
        "confidence": "HIGH",
        "read": True,
    }
    fields.update(overrides)
    return CoverageRecord(**fields)


def test_a_supported_concept_must_have_been_read() -> None:
    with pytest.raises(ValidationError):
        _rec(read=False)
    with pytest.raises(ValidationError):
        _rec(status=CoverageStatus.NOT_READ, read=True)


def test_a_partial_record_names_the_statement_it_backs() -> None:
    with pytest.raises(ValidationError):
        _rec(status=CoverageStatus.PARTIALLY_SUPPORTED)
    assert _rec(status=CoverageStatus.PARTIALLY_SUPPORTED, statement="origin region only")


def test_the_indian_profile_can_support_nothing() -> None:
    with pytest.raises(ValidationError):
        _rec(methodology_profile="PALM_INDIAN_HASTA_SAMUDRIKA")
    assert _rec(
        methodology_profile="PALM_INDIAN_HASTA_SAMUDRIKA",
        status=CoverageStatus.RESEARCH_PENDING,
        read=False,
    )


def test_duplicate_records_are_rejected() -> None:
    with pytest.raises(ValidationError):
        PalmSourceCoverage(manifest_id="M", manifest_version="1", records=(_rec(), _rec()))


def test_only_read_supported_concepts_back_a_rule() -> None:
    manifest = PalmSourceCoverage(
        manifest_id="M",
        manifest_version="1",
        records=(
            _rec(),
            _rec(concept_id="PALM_FEATURE.THUMB", status=CoverageStatus.NOT_READ, read=False),
            _rec(
                concept_id="PALM_FEATURE.NAILS",
                status=CoverageStatus.EXCLUDED_BY_POLICY,
                read=False,
            ),
        ),
    )
    ok = manifest.problems_for_rule(
        "PALM_HA_MAP_LINES_384_393", "para. 384, p. 190", ["PALM_LINE.LIFE"]
    )
    assert ok == ()
    for concept in ("PALM_FEATURE.THUMB", "PALM_FEATURE.NAILS", "PALM_LINE.UNKNOWN"):
        problems = manifest.problems_for_rule(
            "PALM_HA_MAP_LINES_384_393", "para. 384, p. 190", [concept]
        )
        assert problems, concept
    wrong_place = manifest.problems_for_rule(
        "PALM_HA_MAP_LINES_384_393", "para. 999", ["PALM_LINE.LIFE"]
    )
    assert wrong_place


def test_manifest_content_hash_is_deterministic() -> None:
    one = PalmSourceCoverage(manifest_id="M", manifest_version="1", records=(_rec(),))
    two = PalmSourceCoverage(manifest_id="M", manifest_version="1", records=(_rec(),))
    assert one.content_hash == two.content_hash
