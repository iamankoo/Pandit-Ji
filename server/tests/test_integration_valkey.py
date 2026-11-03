"""Valkey/Redis behaviour: counters, TTL, shared rate limits, revocation and degraded operation.

Runs only when ``SERVER_TEST_VALKEY_URL`` points at a Valkey or Redis server.
"""

from __future__ import annotations

import os
import time
import uuid

import pytest
from conftest import AUDIENCE, ISSUER, JWKS, make_token

from pandit_server.auth.oidc import AuthError, StaticKeyProvider, TokenVerifier
from pandit_server.kv import ResilientStore, ValkeyStore
from pandit_server.platform_services import RateLimiter, ResultCache

URL = os.environ.get("SERVER_TEST_VALKEY_URL")
pytestmark = pytest.mark.skipif(not URL, reason="SERVER_TEST_VALKEY_URL is not set")


@pytest.fixture()
def store() -> ValkeyStore:
    assert URL
    return ValkeyStore(URL)


def _k() -> str:
    return "test:" + uuid.uuid4().hex


def test_incr_counts_and_expires(store: ValkeyStore) -> None:
    key = _k()
    assert [store.incr(key, 1), store.incr(key, 1), store.incr(key, 1)] == [1, 2, 3]
    time.sleep(1.2)
    assert store.incr(key, 1) == 1  # the window expired


def test_set_get_delete_and_ping(store: ValkeyStore) -> None:
    key = _k()
    store.set(key, "v", 30)
    assert store.get(key) == "v" and store.ping()
    store.delete(key)
    assert store.get(key) is None


def test_the_rate_limit_is_shared_across_processes(store: ValkeyStore) -> None:
    assert URL
    a, b = RateLimiter(store, 60), RateLimiter(ValkeyStore(URL), 60)  # two "processes"
    who = _k()
    decisions = [
        a.check("t", who, 3).allowed,
        b.check("t", who, 3).allowed,
        a.check("t", who, 3).allowed,
    ]
    assert decisions == [True, True, True]
    assert b.check("t", who, 3).allowed is False
    assert a.check("t", who + "-other", 3).allowed is True


def test_revocation_is_shared_between_verifier_instances(store: ValkeyStore) -> None:
    assert URL

    def verifier(s: ValkeyStore) -> TokenVerifier:
        return TokenVerifier(
            issuer=ISSUER, audience=AUDIENCE, keys=StaticKeyProvider(JWKS), store=s
        )

    one, two = verifier(store), verifier(ValkeyStore(URL))
    token = make_token(f"u-{uuid.uuid4().hex}", jti=uuid.uuid4().hex)
    principal = one.verify(token)
    two.revoke_token(principal)
    with pytest.raises(AuthError) as caught:
        one.verify(token)
    assert caught.value.code == "token_revoked"


def test_the_cache_is_shared_and_scoped(store: ValkeyStore) -> None:
    cache = ResultCache(store, 30)
    ns = _k()
    calls: list[int] = []

    def compute() -> dict[str, int]:
        calls.append(1)
        return {"n": len(calls)}

    assert cache.get_or_compute(ns, "user-a", {"x": 1}, {"v": 1}, compute) == ({"n": 1}, False)
    assert cache.get_or_compute(ns, "user-a", {"x": 1}, {"v": 1}, compute) == ({"n": 1}, True)
    assert cache.get_or_compute(ns, "user-b", {"x": 1}, {"v": 1}, compute)[1] is False  # other user
    assert (
        cache.get_or_compute(ns, "user-a", {"x": 1}, {"v": 2}, compute)[1] is False
    )  # other version


def test_an_unreachable_valkey_degrades_to_a_process_local_store_and_reports_it() -> None:
    dead = ResilientStore(ValkeyStore("redis://127.0.0.1:6399/0"))
    assert dead.incr("k", 10) == 1 and dead.incr("k", 10) == 2
    assert dead.degraded is True and dead.ping() is False
