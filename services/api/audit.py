import json
from typing import Optional, Dict, Any
from .database import AsyncSessionLocal
from .models import AuditLog


async def record_audit_log(
    user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
):
    """Asynchronously records a security or administrative audit log entry."""
    try:
        async with AsyncSessionLocal() as session:
            audit = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details_json=json.dumps(details or {}),
            )
            session.add(audit)
            await session.commit()
    except Exception as e:
        print(f"Warning: Failed to persist audit log: {e}")

