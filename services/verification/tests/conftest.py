from __future__ import annotations

import pytest
from helpers import World, make_world
from pandit_contracts.agent import NarrationClaim
from pandit_contracts.verification import ClaimVerification, ReasonCode, VerificationStatus

from pandit_verification import VerifierConfig


@pytest.fixture(scope="module")
def world() -> World:
    return make_world()


class Judge:
    """Verify one claim and return its single result."""

    def __init__(self, world: World) -> None:
        self.world = world

    def __call__(
        self, claim: NarrationClaim, config: VerifierConfig | None = None, **kw: object
    ) -> ClaimVerification:
        from helpers import make_response

        verifier = self.world.verifier(config, **kw)  # type: ignore[arg-type]
        report = verifier.verify(make_response(claim))
        assert len(report.claims) == 1
        return report.claims[0]


@pytest.fixture()
def judge(world: World) -> Judge:
    return Judge(world)


def codes(result: ClaimVerification) -> set[ReasonCode]:
    return {r.code for r in result.reasons}


def assert_status(
    result: ClaimVerification, status: VerificationStatus, *wanted: ReasonCode
) -> None:
    assert result.status is status, [(r.code.value, r.detail) for r in result.reasons]
    for code in wanted:
        assert code in codes(result), [(r.code.value, r.detail) for r in result.reasons]
    if status is VerificationStatus.VERIFIED:
        assert result.verified_by is not None
    else:
        assert result.verified_by is None
