# bot/services/inventory_service.py
from db.database import db_session
from bot.crud import users_crud, inventory_crud

def fetch_inventory_for_member(target_member):
    with db_session() as dbs:
        user_row = users_crud.get_or_create_user(dbs, target_member)
        items = inventory_crud.fetch_user_inventory_ordered(dbs, user_row.id)
        # also return a resolved display_name for UI
        display_name = user_row.nickname or user_row.display_name or user_row.username
        return user_row, items, display_name