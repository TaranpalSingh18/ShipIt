"""add customer_voice column if missing

Revision ID: 002_customer_voice
Revises: 001_initial
Create Date: 2026-06-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "002_customer_voice"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("projects"):
        return

    columns = {col["name"] for col in inspector.get_columns("projects")}
    if "customer_voice" not in columns:
        op.add_column("projects", sa.Column("customer_voice", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("projects"):
        return

    columns = {col["name"] for col in inspector.get_columns("projects")}
    if "customer_voice" in columns:
        op.drop_column("projects", "customer_voice")
