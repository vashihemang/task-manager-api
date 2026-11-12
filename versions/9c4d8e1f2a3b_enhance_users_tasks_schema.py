from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c4d8e1f2a3b'
down_revision: Union[str, Sequence[str], None] = 'e0624a62042b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with teacher-task relationship, deadlines, timestamps, indexes, and constraints."""
    op.execute("UPDATE users SET status = 'active' WHERE status IS NULL")
    op.alter_column(
        'users',
        'status',
        existing_type=sa.String(length=20),
        nullable=False,
        server_default=sa.text("'active'"),
    )
    op.add_column(
        'users',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index('ix_users_role', 'users', ['role'], unique=False)
    op.create_check_constraint(
        'ck_users_role',
        'users',
        "role IN ('student', 'teacher')",
    )
    op.create_check_constraint(
        'ck_users_status',
        'users',
        "status IN ('active', 'inactive')",
    )

    op.execute("UPDATE tasks SET status = 'completed' WHERE status = 'done'")
    op.alter_column(
        'tasks',
        'status',
        existing_type=sa.String(length=20),
        nullable=False,
        server_default=sa.text("'pending'"),
    )
    op.add_column(
        'tasks',
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'tasks',
        sa.Column('assigned_by_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'tasks',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        'fk_tasks_assigned_by_id_users',
        'tasks',
        'users',
        ['assigned_by_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_tasks_user_id', 'tasks', ['user_id'], unique=False)
    op.create_index('ix_tasks_assigned_by_id', 'tasks', ['assigned_by_id'], unique=False)
    op.create_index('ix_tasks_status', 'tasks', ['status'], unique=False)
    op.create_check_constraint(
        'ck_tasks_status',
        'tasks',
        "status IN ('pending', 'in_progress', 'completed')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_tasks_status', 'tasks', type_='check')
    op.drop_index('ix_tasks_status', table_name='tasks')
    op.drop_index('ix_tasks_assigned_by_id', table_name='tasks')
    op.drop_index('ix_tasks_user_id', table_name='tasks')
    op.drop_constraint('fk_tasks_assigned_by_id_users', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'updated_at')
    op.drop_column('tasks', 'assigned_by_id')
    op.drop_column('tasks', 'deadline')
    op.execute("UPDATE tasks SET status = 'done' WHERE status = 'completed'")

    op.drop_constraint('ck_users_status', 'users', type_='check')
    op.drop_constraint('ck_users_role', 'users', type_='check')
    op.drop_index('ix_users_role', table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_column('users', 'updated_at')
    op.alter_column(
        'users',
        'status',
        existing_type=sa.String(length=20),
        nullable=True,
        server_default=None,
    )
