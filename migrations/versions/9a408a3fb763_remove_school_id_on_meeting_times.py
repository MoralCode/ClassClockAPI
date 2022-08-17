"""remove school_id on meeting times

Revision ID: 9a408a3fb763
Revises: 2399c50496f7
Create Date: 2022-06-05 22:45:11.620997

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '9a408a3fb763'
down_revision = '2399c50496f7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('bellschedulemeetingtimes_FK', table_name='bellschedulemeetingtimes')
    op.drop_column('bellschedulemeetingtimes', 'school_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('bellschedulemeetingtimes', sa.Column('school_id', sa.BINARY(length=16), nullable=False))
    op.create_index('bellschedulemeetingtimes_FK', 'bellschedulemeetingtimes', ['school_id'], unique=False)
    # ### end Alembic commands ###