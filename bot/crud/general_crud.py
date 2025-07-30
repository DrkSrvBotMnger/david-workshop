from db.schema import EventLog
from datetime import datetime


## Internal functions

# Log function
def log_change(*,session, log_model, fk_field: str, fk_value: int, action: str, performed_by: str, description: str = None):
    """Generic logging for any object with a log table."""
    kwargs = {
        fk_field: fk_value,
        "action": action,
        "performed_by": performed_by,
        "timestamp": datetime.utcnow().isoformat(),
        "description": description
    }
    log_entry = log_model(**kwargs)
    session.add(log_entry)
    return log_entry