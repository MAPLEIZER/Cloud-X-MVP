"""Add durable scan queue update timestamps and queued default.

Revision ID: 20260814_0002
Revises: 20260814_0001
Create Date: 2026-08-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260814_0002"
down_revision: Union[str, Sequence[str], None] = "20260814_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.alter_column(
        "scan",
        "status",
        existing_type=sa.String(length=20),
        server_default="queued",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "scan",
        "status",
        existing_type=sa.String(length=20),
        server_default="submitted",
        existing_nullable=False,
    )
    op.drop_column("scan", "updated_at")
