"""create snapshots schema

Revision ID: abb9363cd21a
Revises: 
Create Date: 2023-06-20 15:29:35.690770

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'abb9363cd21a'
down_revision = None
branch_labels = None
depends_on = None

language_enum = sa.Enum('JAVA', 'CPP', 'JAVASCRIPT', 'PYTHON', 'RUBY', 'SWIFT', 'GO', 'CSHARP', name='snapshotlanguage')
state_enum = sa.Enum('SNAPSHOT_FAILED', 'NOT_BUILT', 'BUILD_IN_PROGRESS', 'BUILD_FAILED', 'NOT_ANALYZED', 'ANALYSIS_FAILED', 'ANALYSIS_IN_PROGRESS', 'ANALYZED', name='snapshotstate')

def upgrade() -> None:
    op.create_table('snapshots',
    sa.Column('global_id', sa.String(length=64), nullable=False),
    sa.Column('source_id', sa.String(length=64), nullable=False),
    sa.Column('project_url', sa.String(length=2048), nullable=False),
    sa.Column('branch', sa.String(length=255), nullable=False),
    sa.Column('commit', sa.String(length=40), nullable=False),
    sa.Column('language', language_enum, nullable=False),
    sa.Column('state', state_enum, nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('project_url', 'branch', 'commit', 'language', name=op.f('pk_snapshots'))
    )


def downgrade() -> None:
    op.drop_table('snapshots')
    language_enum.drop(op.get_bind(), checkfirst=False)
    state_enum.drop(op.get_bind(), checkfirst=False)
