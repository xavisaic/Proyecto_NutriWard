import uuid
from typing import Any

from sqlmodel import Session

from app.models.audit_log import AuditLog


def record_audit(
    session: Session,
    *,
    action: str,
    actor_user_id: uuid.UUID | None,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    admission_id: uuid.UUID | None = None,
) -> AuditLog:
    event = AuditLog(
        action=action,
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
        admission_id=admission_id,
    )
    session.add(event)
    return event
