"""Verified OIDC identities; short-lived internal tokens for trusted workers."""
import time
import logging
from functools import lru_cache
from contextvars import ContextVar
import jwt
from fastapi import HTTPException
from config import settings
logger = logging.getLogger(__name__)
current_claims = ContextVar("claims", default={})
ROLES = {"requester", "procurement", "approver", "ap_clerk", "executive", "admin"}
@lru_cache(maxsize=1)
def _jwks():
    if not settings.oidc_issuer: raise HTTPException(503, "OIDC_ISSUER is not configured")
    url = settings.oidc_jwks_url or settings.oidc_issuer.rstrip("/") + "/protocol/openid-connect/certs"
    return jwt.PyJWKClient(url, cache_keys=True, timeout=10)
def verify_token(token):
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
        if unverified.get("iss") == "aria-worker":
            if len(settings.service_secret) < 32: raise ValueError("Internal authentication not configured")
            claims = jwt.decode(token, settings.service_secret, algorithms=["HS256"],
                audience="aria-api", issuer="aria-worker", options={"require": ["exp", "sub", "email"]})
        else:
            key = _jwks().get_signing_key_from_jwt(token).key
            claims = jwt.decode(token, key, algorithms=["RS256"], audience=settings.oidc_audience,
                issuer=settings.oidc_issuer, options={"require": ["exp", "sub", "email"]})
        roles = set(claims.get("realm_access", {}).get("roles", [])) & ROLES
        claims["p2p_role"] = next((r for r in ["admin", "procurement", "approver", "ap_clerk", "executive", "requester"] if r in roles), "")
        if not claims["p2p_role"]: raise ValueError("No application role assigned")
        return claims
    except HTTPException: raise
    except Exception as exc:
        # Only the exception category: never log bearer tokens or claim values.
        logger.warning("Authentication rejected: %s", type(exc).__name__)
        raise HTTPException(401, "Invalid or expired authentication token") from exc

def mint_internal_token(claims):
    if len(settings.service_secret) < 32: raise RuntimeError("SERVICE_SECRET must contain at least 32 characters")
    return jwt.encode({"iss": "aria-worker", "aud": "aria-api", "sub": claims["sub"],
        "email": claims["email"], "realm_access": {"roles": [claims["p2p_role"]]},
        "department": claims.get("department", ""), "exp": int(time.time()) + settings.job_timeout_seconds + 120},
        settings.service_secret, algorithm="HS256")
def claims_from_header(header):
    if not header or not header.startswith("Bearer "): raise HTTPException(401, "Authentication required")
    return verify_token(header[7:])
def _jwt_claims(request):
    return getattr(request.state, "claims", None) or claims_from_header(request.headers.get("authorization"))
def get_authenticated_user(request): return _jwt_claims(request)["sub"]
def require_authenticated_user(request): return get_authenticated_user(request)
def get_user_email(request): return _jwt_claims(request)["email"]
def get_user_department(request): return _jwt_claims(request).get("department", "")
def require_roles(request, *roles):
    claims = _jwt_claims(request)
    if claims["p2p_role"] not in roles: raise HTTPException(403, "This role cannot perform that action")
    return claims
