"""add reports table

Revision ID: 003_reports
Revises: 002_customer_voice
Create Date: 2026-10-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "003_reports"
down_revision: Union[str, None] = "002_customer_voice"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if inspect(op.get_bind()).has_table("reports"):
        return
    op.create_table(
        "reports",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("product_name", sa.String(), nullable=True),
        sa.Column("verdict", sa.String(), nullable=True),
        sa.Column("readiness", sa.Integer(), nullable=True),
        sa.Column("report_json", sa.JSON(), nullable=True),
        sa.Column("pdf_filename", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reports_project_id"), "reports", ["project_id"], unique=False)
    op.create_index(op.f("ix_reports_user_id"), "reports", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reports_user_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_project_id"), table_name="reports")
    op.drop_table("reports")
