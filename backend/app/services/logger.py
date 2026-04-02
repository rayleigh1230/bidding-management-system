from ..models.operation_log import OperationLog


def log_operation(db, user_id: int, action: str, entity_type: str, entity_id: int, detail: str = ""):
    """Create an OperationLog record. Does NOT commit — caller's commit handles it."""
    log = OperationLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
    )
    db.add(log)
