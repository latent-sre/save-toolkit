"""Optional bearer adapter when the app's identity integration accepts bearer tokens.

Prefer the project's native/corporate-SSO integration. This adapter supplies neither an identity
provider nor a token parser; the verifier owns token validation and the trusted principal mapping.
Bearer tokens need not be JWTs. Attach authenticated at the protected router boundary, use
Authenticated when a handler needs the caller, and enforce object authorization separately.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Principal:
    subject: str
    scopes: frozenset[str] = field(default_factory=frozenset)


# Return None for an invalid, expired or forged token. Raising means verification itself failed
# (for example, the identity provider is unreachable): that is a 503, not a 401.
TokenVerifier = Callable[[str], Awaitable[Principal | None]]

_bearer = HTTPBearer(scheme_name="bearer", auto_error=False)


def configure_bearer_auth(app: FastAPI, verify: TokenVerifier) -> None:
    """Configure the optional adapter before serving requests; this does not protect routes."""
    app.state.bearer_token_verifier = verify


async def authenticated(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    """Require a verified principal and declare bearer security in the OpenAPI document."""
    challenge = {"WWW-Authenticate": "Bearer"}
    if credentials is None:
        raise HTTPException(401, "A valid bearer token is required.", headers=challenge)
    verify: TokenVerifier | None = getattr(request.app.state, "bearer_token_verifier", None)
    if verify is None:
        raise HTTPException(503, "Credentials could not be verified; try again shortly.")
    try:
        principal = await verify(credentials.credentials)
    except Exception:
        logger.warning("Token verification failed", exc_info=False)
        raise HTTPException(503, "Credentials could not be verified; try again shortly.") from None
    if principal is None:
        raise HTTPException(401, "A valid bearer token is required.", headers=challenge)
    return principal


Authenticated = Annotated[Principal, Depends(authenticated)]
