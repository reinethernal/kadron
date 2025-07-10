"""initial migration"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "polls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("anonymous", sa.Boolean(), server_default="0"),
        sa.Column("time_limit", sa.DateTime()),
        sa.Column("scheduled_time", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "poll_id", sa.Integer(), sa.ForeignKey("polls.id", ondelete="CASCADE")
        ),
        sa.Column("text", sa.Text()),
        sa.Column("type", sa.String()),
        sa.Column("options", sa.Text()),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), unique=True),
        sa.Column("username", sa.String()),
        sa.Column("category", sa.String(), server_default="Новичок"),
        sa.Column("last_activity", sa.DateTime()),
        sa.Column("warnings", sa.Integer(), server_default="0"),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chat_id", sa.Integer()),
        sa.Column("user_id", sa.Integer()),
        sa.Column("timestamp", sa.DateTime()),
    )

    op.create_table(
        "responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "poll_id", sa.Integer(), sa.ForeignKey("polls.id", ondelete="CASCADE")
        ),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
        ),
        sa.Column("user_id", sa.Integer()),
        sa.Column("answer", sa.Text()),
        sa.Column("timestamp", sa.DateTime()),
    )


def downgrade():
    op.drop_table("responses")
    op.drop_table("messages")
    op.drop_table("users")
    op.drop_table("questions")
    op.drop_table("polls")
