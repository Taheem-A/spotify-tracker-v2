import asyncio
import pytest

from app.auth import pkce


def test_oauth_state_mismatch_is_rejected():
    pkce.create_authorization_url()
    with pytest.raises(ValueError, match="state mismatch"):
        asyncio.run(pkce.exchange_code("unused-code", "definitely-wrong-state"))


def test_oauth_exchange_requires_pending_state():
    pkce._verifier = None
    pkce._pending_state = None
    with pytest.raises(RuntimeError, match="authorization state missing"):
        asyncio.run(pkce.exchange_code("unused-code", "unused-state"))
