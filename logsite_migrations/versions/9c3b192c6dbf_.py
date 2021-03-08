"""empty message

Revision ID: 9c3b192c6dbf
Revises: 4680022c11c2
Create Date: 2018-04-27 23:29:21.960845

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '9c3b192c6dbf'
down_revision = '4680022c11c2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('line',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('game_id', sa.Integer(), nullable=False),
    sa.Column('clearance', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['game_id'], ['game.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('line')
    # ### end Alembic commands ###
