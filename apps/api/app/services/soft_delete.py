from __future__ import annotations

from datetime import datetime


def active_filter(model):
    return model.is_deleted.is_(False)


def deleted_filter(model):
    return model.is_deleted.is_(True)


def mark_deleted(instance, actor_id: int | None) -> None:
    instance.is_deleted = True
    instance.deleted_at = datetime.utcnow()
    instance.deleted_by_user_id = actor_id


def restore_deleted(instance) -> None:
    instance.is_deleted = False
    instance.deleted_at = None
    instance.deleted_by_user_id = None
