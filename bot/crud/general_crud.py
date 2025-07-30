from db.schema import EventLog
from datetime import datetime


## Internal functions

# Log function
def log_event_change(*,session, event_id, action, performed_by, description=None):
    log_entry = EventLog(
        event_id=event_id,
        action=action,
        performed_by=performed_by,
        timestamp=str(datetime.utcnow()),
        description=description
    )
    session.add(log_entry)