"""Create the initial Cloud-X scan schema.

Revision ID: 20260814_0001
Revises:
Create Date: 2026-08-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260814_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scan",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("tool", sa.String(length=50), nullable=False, server_default="nmap"),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("scan_type", sa.String(length=50), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="submitted"
        ),
        sa.Column("progress", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("results", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", name="uq_scan_job_id"),
    )


def downgrade() -> None:
    op.drop_table("scan")
