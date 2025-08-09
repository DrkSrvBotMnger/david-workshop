├─ bot/
│  ├─ app.py
│  ├─ cogs/
│  │  ├─ admin/
│  │  │  ├─ events_cog.py
│  │  │  ├─ rewards_cog.py
│  │  │  ├─ actions_cog.py
│  │  │  └─ shop_cog.py
│  │  └─ user/
│  │     ├─ profile_cog.py              
│  │     ├─ event_cog.py
│  │     └─ shop_cog.py
│  │
│  ├─ ui/
│  │  ├─ common/
│  │  │  ├─ base_view.py
│  │  │  ├─ paginator.py                
│  │  │  └─ confirms.py                 
│  │  ├─ admin/
│  │  │  ├─ events_views.py
│  │  │  ├─ rewards_views.py
│  │  │  ├─ actions_views.py
│  │  │  └─ shop_views.py
│  │  ├─ user/
│  │  │  ├─ profile_views.py            
│  │  │  └─ inventory_views.py          
│  │  └─ renderers/
│  │     ├─ profile_card.py             
│  │     └─ badge_loader.py             
│  │
│  ├─ services/
│  │  ├─ events_service.py
│  │  ├─ rewards_service.py
│  │  ├─ actions_service.py
│  │  ├─ shop_service.py
│  │  └─ users_service.py
│  │
│  ├─ crud/
│  │  ├─ events_crud.py
│  │  ├─ rewards_crud.py
│  │  ├─ actions_crud.py
│  │  ├─ action_events_crud.py
│  │  ├─ reward_events_crud.py
│  │  ├─ users_crud.py
│  │  └─ inventory_crud.py              
│  │
│  ├─ domain/
│  │  ├─ dto.py
│  │  ├─ validators.py
│  │  └─ mapping.py
│  │
│  ├─ utils/
│  │  ├─ discord_helpers.py             
│  │  ├─ formatting.py                  
│  │  ├─ parsing.py                     
│  │  ├─ permissions.py                
│  │  ├─ emoji.py                       
│  │  └─ logging.py
│  │
│  └─ config/
│     ├─ __init__.py                    
│     ├─ environments.py                
│     └─ constants.py                 
│
├─ db/
│  ├─ database.py
│  ├─ schema.py
│  └─ migrations/
│
├─ tests/
│  ├─ cogs/
│  ├─ services/
│  ├─ crud/
│  ├─ ui/
│  └─ utils/
└─ docs/