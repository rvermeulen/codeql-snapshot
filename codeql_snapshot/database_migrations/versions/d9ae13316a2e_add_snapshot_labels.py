"""Add snapshot labels

Revision ID: d9ae13316a2e
Revises: abb9363cd21a
Create Date: 2023-06-21 16:41:13.941523

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9ae13316a2e'
down_revision = 'abb9363cd21a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(op.f('uq_snapshots_global_id'), 'snapshots', ['global_id'])
    op.create_table('snapshot_labels',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('snapshot_global_id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['snapshot_global_id'], ['snapshots.global_id'], name=op.f('fk_snapshot_labels_snapshot_global_id_snapshots')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_snapshot_labels'))
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(op.f('uq_snapshots_global_id'), 'snapshots', type_='unique')
    op.drop_table('snapshot_labels')
    # ### end Alembic commands ###
