def get_tenant_tasks(task_records: list[dict], requesting_tenant: str) -> list[dict]:
    """Return only records owned by the requesting tenant."""
    return [
        record for record in task_records
        if record.get("tenant_id") == requesting_tenant
    ]

def can_access_task(task_record: dict, requesting_tenant: str) -> bool:
    """Simple tenant-isolation check; this is not production authentication."""
    return task_record.get("tenant_id") == requesting_tenant
