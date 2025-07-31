if reward.reward_type == "preset" and not reward.use_message_id:
    raise ValueError("Cannot attach a preset reward that has not been published.")