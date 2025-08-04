

action event can be linked several timeswe would need a way to differentiate them because helper text and points are _de_optionalize_fwd_ref_union_typesadding a custom id to the table?
missing end msg to tell admin the link was done



# ---------------------------
# ACTION EVENTS
# ---------------------------




def update_action_event(
    session,
    action_event_id,
    points_granted=None,
    reward_event_id=None,
    self_reportable=None,
    input_help_text=None,
    modified_by=None,
    reason=None
):
    ae = session.get(ActionEvent, action_event_id)
    if not ae:
        return None

    if points_granted is not None:
        ae.points_granted = points_granted
    if reward_event_id is not None:
        ae.reward_event_id = reward_event_id
    if self_reportable is not None:
        ae.self_reportable = self_reportable
    if input_help_text is not None:
        ae.input_help_text = input_help_text

    general_crud.log_change(
        session=session,
        table_name="action_event_logs",
        target_id=action_event_id,
        action="edit",
        performed_by=modified_by,
        description=reason or f"Edited ActionEvent {action_event_id}."
    )
    return ae.id


def delete_action_event(session, action_event_id, deleted_by=None, reason=None):
    ae = session.get(ActionEvent, action_event_id)
    if not ae:
        return None
    session.delete(ae)

    log_change(
        session=session,
        table_name="action_event_logs",
        target_id=action_event_id,
        action="delete",
        performed_by=deleted_by,
        description=reason or f"Unlinked ActionEvent {action_event_id}."
    )
    return action_event_id
