from bot.utils import now_iso


# Log function
def log_change(*,session, log_model, fk_field: str, fk_value: int, action: str, performed_by: str, description: str = None, forced: bool = False):
    """Generic logging for any object with a log table."""

    if forced:
        description = f"⚠️ **FORCED CHANGE** — {description}" if description else "⚠️ **FORCED CHANGE**"
        
    kwargs = {
        fk_field: fk_value,
        "action": action,
        "performed_by": performed_by,
        "timestamp": now_iso(),
        "description": description
    }
    log_entry = log_model(**kwargs)
    session.add(log_entry)
    return log_entry