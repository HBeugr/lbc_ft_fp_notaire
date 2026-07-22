"""Middleware de résolution du cabinet + portier d'accès.

Rôle : à partir du JWT, identifier le cabinet et le poser dans le `ContextVar`
**avant** que FastAPI ne résolve les dépendances de l'endpoint. C'est ce qui
permet à `Depends(get_db)` de rester inchangé sur les 113 points d'injection
existants tout en ouvrant une session sur le bon schéma.

Middleware ASGI pur (et non `BaseHTTPMiddleware`) : c'est indispensable ici, car
`BaseHTTPMiddleware` exécute l'endpoint dans une tâche distincte, où le
`ContextVar` posé ne serait pas visible.

Il porte aussi le **portier** : un cabinet suspendu (impayé futur, décision
d'exploitation) est refoulé ici, une fois pour toutes, plutôt que dans chaque
router.
"""
from __future__ import annotations

import json

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core import security, tenant_resolver
from app.core.logging import logger
from app.core.tenant_context import reset_current_tenant, set_current_tenant

# Chemins servis hors de tout cabinet : login (le tenant n'est pas encore connu),
# santé, documentation, et toute la console d'exploitation qui ne touche jamais
# aux données métier.
_TENANT_FREE_PREFIXES = (
    "/api/auth/login",
    "/api/auth/logout",
    "/api/super-admin",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
)

# Endpoints restant accessibles à un cabinet suspendu, pour qu'un utilisateur
# puisse constater la situation et se déconnecter proprement.
_SUSPENDED_ALLOWED = (
    "/api/auth/refresh",
    "/api/auth/logout",
    "/api/users/me",
    "/api/tenant/me",
)


async def _send_json(send: Send, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({"type": "http.response.body", "body": body})


def _extract_token(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"authorization":
            raw = value.decode("latin-1")
            if raw.lower().startswith("bearer "):
                return raw[7:].strip()
    # Le flux SSE des alertes ne peut pas porter d'en-tête : le token y transite
    # en paramètre de requête.
    query = scope.get("query_string", b"").decode("latin-1")
    for part in query.split("&"):
        if part.startswith("token="):
            from urllib.parse import unquote

            return unquote(part[6:])
    return None


class TenantMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        if path.startswith(_TENANT_FREE_PREFIXES):
            await self.app(scope, receive, send)
            return

        token = _extract_token(scope)
        if not token:
            # Pas de token : on laisse l'endpoint répondre 401 lui-même, afin de
            # conserver le contrat d'erreur existant.
            await self.app(scope, receive, send)
            return

        try:
            payload = security.decode_token(token)
        except Exception:
            await self.app(scope, receive, send)
            return

        tenant_id = payload.get("tid")
        if not tenant_id:
            await _send_json(send, 401, {"detail": "Session sans cabinet — reconnectez-vous."})
            return

        tenant = await tenant_resolver.get_by_id(tenant_id)
        if tenant is None:
            logger.warning("tenant.unknown", tenant_id=tenant_id, path=path)
            await _send_json(send, 401, {"detail": "Cabinet introuvable."})
            return

        # Le `code` est indispensable côté client : c'est lui qui distingue un
        # cabinet bloqué d'un défaut d'authentification. Sans lui, l'interface
        # traitait le refus comme un jeton invalide et déconnectait l'utilisateur
        # au lieu de lui expliquer la situation.
        if tenant.statut == "archive":
            await _send_json(send, 403, {
                "code": "tenant_archived",
                "detail": "Ce cabinet est archivé. Contactez l'administrateur de la plateforme.",
            })
            return

        if tenant.statut == "suspendu" and not path.startswith(_SUSPENDED_ALLOWED):
            await _send_json(send, 402, {
                "code": "tenant_suspended",
                "detail": "Accès suspendu. Contactez l'administrateur de la plateforme "
                          "pour régulariser la situation de votre cabinet.",
            })
            return

        context_token = set_current_tenant(tenant)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_current_tenant(context_token)
