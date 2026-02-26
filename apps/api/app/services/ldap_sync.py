import secrets
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import LdapSetting, User

VALID_ROLES = {"OWNER", "ADMIN", "ACCOUNTANT"}


def get_or_create_ldap_setting(db: Session) -> LdapSetting:
    setting = db.execute(select(LdapSetting).order_by(LdapSetting.id.asc())).scalar_one_or_none()
    if setting is not None:
        return setting
    setting = LdapSetting()
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def parse_server_url(server_url: str) -> tuple[str, int, bool]:
    raw = (server_url or "").strip()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="LDAP server_url is required")

    if "://" not in raw:
        host = raw
        port = 389
        use_ssl = False
        return host, port, use_ssl

    parsed = urlparse(raw)
    host = parsed.hostname or ""
    if not host:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid LDAP server_url")
    use_ssl = parsed.scheme.lower() == "ldaps"
    port = parsed.port or (636 if use_ssl else 389)
    return host, port, use_ssl


def _first_attr_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        if not value:
            return ""
        return str(value[0]).strip()
    return str(value).strip()


def sync_ldap_users(db: Session, setting: LdapSetting) -> dict[str, int]:
    if not setting.enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="LDAP is not enabled")
    if not setting.bind_dn or not setting.bind_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="LDAP bind account is not configured")
    if not setting.base_dn:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="LDAP base_dn is required")

    default_role = setting.default_role if setting.default_role in VALID_ROLES else "ACCOUNTANT"
    search_base = setting.user_base_dn.strip() or setting.base_dn.strip()
    user_filter = setting.user_filter.strip() or "(uid=*)"

    host, port, use_ssl = parse_server_url(setting.server_url)

    # Lazy import to avoid hard dependency at module import time.
    from ldap3 import ALL, Connection, Server

    try:
        server = Server(host=host, port=port, use_ssl=use_ssl, get_info=ALL)
        conn = Connection(server, user=setting.bind_dn, password=setting.bind_password, auto_bind=True)
        conn.search(
            search_base=search_base,
            search_filter=user_filter,
            attributes=[setting.username_attr, setting.display_name_attr],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LDAP connection failed: {exc}",
        ) from exc

    created_count = 0
    updated_count = 0
    skipped_count = 0
    total_found = len(conn.entries)

    for entry in conn.entries:
        attr_data = entry.entry_attributes_as_dict
        username = _first_attr_value(attr_data.get(setting.username_attr))
        entry_dn = str(entry.entry_dn).strip()

        if not username:
            skipped_count += 1
            continue

        user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if user is None:
            db.add(
                User(
                    username=username,
                    password_hash=hash_password(secrets.token_urlsafe(16)),
                    role=default_role,
                    is_active=True,
                    auth_source="LDAP",
                    ldap_dn=entry_dn,
                )
            )
            created_count += 1
            continue

        changed = False
        if user.auth_source != "LDAP":
            user.auth_source = "LDAP"
            changed = True
        if user.ldap_dn != entry_dn:
            user.ldap_dn = entry_dn
            changed = True
        if changed:
            updated_count += 1
        else:
            skipped_count += 1

    conn.unbind()
    db.commit()
    return {
        "total_found": total_found,
        "created_count": created_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
    }
