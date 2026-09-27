"""Minimum-age gate for marriage matching (Phase 11 product policy, CM-04;
`PRODUCT_POLICIES.md` "Minors").

Completed years between the civil birth date and the caller's civil date.
A 29 February birthday is reached on 1 March in a common year (the later,
more conservative date). A date before the birth date is not verifiable.
Nothing is inferred from an incomplete date: the request model requires a
full year, month and day.
"""

from __future__ import annotations

import datetime as dt

from pandit_astro_engine.compatibility.constants import (
    MINIMUM_AGE_YEARS,
    MatchReason,
    Participant,
)
from pandit_astro_engine.compatibility.models import ParticipantPolicyRecord


def completed_years(birth_date: dt.date, as_of: dt.date) -> int | None:
    if as_of < birth_date:
        return None
    before_birthday = (as_of.month, as_of.day) < (birth_date.month, birth_date.day)
    return as_of.year - birth_date.year - (1 if before_birthday else 0)


def check_participant(
    participant: Participant, birth_date: dt.date, as_of: dt.date
) -> ParticipantPolicyRecord:
    years = completed_years(birth_date, as_of)
    if years is None:
        return ParticipantPolicyRecord(
            participant=participant, minimum_age_met=None, reason=MatchReason.AGE_NOT_VERIFIABLE
        )
    if years < MINIMUM_AGE_YEARS:
        return ParticipantPolicyRecord(
            participant=participant,
            minimum_age_met=False,
            reason=MatchReason.PARTICIPANT_UNDER_MINIMUM_AGE,
        )
    return ParticipantPolicyRecord(participant=participant, minimum_age_met=True)
