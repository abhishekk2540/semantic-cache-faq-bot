import os
import logging
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import jwt
from jwt import PyJWKClient

from .config import CLERK_FRONTEND_API

logger = logging.getLogger(__name__)

bearer = HTTPBearer(auto_error=False)

_jwk_clients = {}


def _get_jwk_client_for_issuer(issuer: str):
    """Cache and return a PyJWKClient for the given Clerk issuer/frontend API."""
    issuer = issuer.rstrip("/")
    if issuer not in _jwk_clients:
        jwks_url = f"{issuer}/.well-known/jwks.json"
        _jwk_clients[issuer] = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)
    return _jwk_clients[issuer]


def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    """Dependency: validates the Clerk-issued JWT and returns the user info.

    Returns dict with:
      - id:       Clerk user id  (e.g. "user_2x...")
      - username: preferred identifier extracted from claims
    """
    if creds is None:
        raise HTTPException(401, "Login required – send a Clerk session token")

    token = creds.credentials
    try:
        # Determine the issuer: prefer config, or fallback to token's own `iss` claim
        issuer = CLERK_FRONTEND_API
        if not issuer:
            unverified = jwt.decode(token, options={"verify_signature": False})
            issuer = unverified.get("iss", "")

        if not issuer:
            raise ValueError("No Clerk issuer found in config or token")

        jwk_client = _get_jwk_client_for_issuer(issuer)
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        data = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired – please sign in again")
    except Exception as exc:
        logger.warning("Clerk JWT verification failed: %s", exc)
        raise HTTPException(401, f"Invalid token: {exc}")

    user_id = data.get("sub", "")
    username = (
        data.get("username")
        or data.get("email")
        or data.get("name")
        or user_id
    )
    return {"id": user_id, "username": username}
