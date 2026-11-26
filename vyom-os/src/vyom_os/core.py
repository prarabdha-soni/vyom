"""Request context and domain errors shared by the services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from vyom_os.audit import Actor
from vyom_os.security import Authorizer
from vyom_os.tenancy import TenantContext

if TYPE_CHECKING:
    from vyom_os.ai.gateway import AiGateway


class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFound(DomainError):
    status_code = 404


class Forbidden(DomainError):
    status_code = 403


class Conflict(DomainError):
    status_code = 409


class InvalidInput(DomainError):
    status_code = 422


class Unavailable(DomainError):
    status_code = 503


_ACTION_TEXT = {
    "case.assess_causality": "Only a safety physician records causality.",
    "case.approve": "Only a safety physician or the QPPV approves cases.",
    "case.approve_serious": "Only a safety physician or the QPPV approves serious cases.",
    "report.signoff": "Only the QPPV signs off periodic reports.",
}


@dataclass(frozen=True)
class Ctx:
    """Who is acting, for which tenant, on which day."""

    tenant: TenantContext
    actor: Actor
    today: date
    authorizer: Authorizer
    gateway: AiGateway

    def can(self, action: str) -> bool:
        return self.authorizer.allowed(self.actor.role, action)

    def require(self, action: str) -> None:
        if not self.can(action):
            raise Forbidden(_ACTION_TEXT.get(action, f"Your role does not allow {action}."))
