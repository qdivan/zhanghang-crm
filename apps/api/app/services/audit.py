from typing import Optional, Union

from sqlalchemy.orm import Session

from app.models import OperationLog


def write_operation_log(
    db: Session,
    *,
    actor_id: Optional[int],
    action: str,
    entity_type: str = "",
    entity_id: Optional[Union[int, str]] = None,
    detail: str = "",
) -> None:
    db.add(
        OperationLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else "",
            detail=detail,
        )
    )
