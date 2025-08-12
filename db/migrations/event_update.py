def upgrade():
    op.alter_column("events", "event_status", server_default=None)

def downgrade():
    op.alter_column("events", "event_status", server_default="draft")