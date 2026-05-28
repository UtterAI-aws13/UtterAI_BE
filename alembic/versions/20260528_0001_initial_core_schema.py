"""Initial core schema for users, children, sessions, and child access grants."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers are used by Alembic to order migrations consistently.
revision = "20260528_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the first set of tables required for ownership and access rules."""

    user_role = sa.Enum(
        "ADMIN",
        "THERAPIST",
        "GUARDIAN",
        "VIEWER",
        name="user_role",
    )
    user_status = sa.Enum("ACTIVE", "INACTIVE", name="user_status")
    child_status = sa.Enum("ACTIVE", "DELETED", name="child_status")
    session_status = sa.Enum(
        "CREATED",
        "AUDIO_UPLOADING",
        "AUDIO_UPLOADED",
        "ANALYSIS_REQUESTED",
        "ANALYSIS_PROCESSING",
        "ANALYSIS_COMPLETED",
        "REPORT_READY",
        "FAILED",
        "DELETED",
        name="session_status",
    )
    access_grant_level = sa.Enum(
        "VIEW_RESULT",
        "VIEW_AND_DOWNLOAD",
        name="access_grant_level",
    )
    access_grant_status = sa.Enum(
        "ACTIVE",
        "REVOKED",
        name="access_grant_status",
    )

    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    user_status.create(bind, checkfirst=True)
    child_status.create(bind, checkfirst=True)
    session_status.create(bind, checkfirst=True)
    access_grant_level.create(bind, checkfirst=True)
    access_grant_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column(
            "status",
            user_status,
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "children",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("therapist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(length=20), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column(
            "status",
            child_status,
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["therapist_id"],
            ["users.id"],
            name="fk_children_therapist_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_children"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("therapist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("session_type", sa.String(length=100), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column(
            "status",
            session_status,
            nullable=False,
            server_default="CREATED",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.id"],
            name="fk_sessions_child_id_children",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["therapist_id"],
            ["users.id"],
            name="fk_sessions_therapist_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sessions"),
    )

    op.create_table(
        "child_access_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grantee_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("granted_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_level", access_grant_level, nullable=False),
        sa.Column(
            "status",
            access_grant_status,
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.id"],
            name="fk_child_access_grants_child_id_children",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["grantee_user_id"],
            ["users.id"],
            name="fk_child_access_grants_grantee_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"],
            ["users.id"],
            name="fk_child_access_grants_granted_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_child_access_grants"),
        sa.UniqueConstraint(
            "child_id",
            "grantee_user_id",
            name="uq_child_access_grants_child_grantee",
        ),
    )

    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_children_therapist_id", "children", ["therapist_id"], unique=False)
    op.create_index("ix_sessions_child_id", "sessions", ["child_id"], unique=False)
    op.create_index("ix_sessions_therapist_id", "sessions", ["therapist_id"], unique=False)
    op.create_index(
        "ix_child_access_grants_child_id",
        "child_access_grants",
        ["child_id"],
        unique=False,
    )
    op.create_index(
        "ix_child_access_grants_grantee_user_id",
        "child_access_grants",
        ["grantee_user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop tables and enum types in reverse dependency order."""

    op.drop_index("ix_child_access_grants_grantee_user_id", table_name="child_access_grants")
    op.drop_index("ix_child_access_grants_child_id", table_name="child_access_grants")
    op.drop_index("ix_sessions_therapist_id", table_name="sessions")
    op.drop_index("ix_sessions_child_id", table_name="sessions")
    op.drop_index("ix_children_therapist_id", table_name="children")
    op.drop_index("ix_users_email", table_name="users")

    op.drop_table("child_access_grants")
    op.drop_table("sessions")
    op.drop_table("children")
    op.drop_table("users")

    bind = op.get_bind()
    sa.Enum(name="access_grant_status").drop(bind, checkfirst=True)
    sa.Enum(name="access_grant_level").drop(bind, checkfirst=True)
    sa.Enum(name="session_status").drop(bind, checkfirst=True)
    sa.Enum(name="child_status").drop(bind, checkfirst=True)
    sa.Enum(name="user_status").drop(bind, checkfirst=True)
    sa.Enum(name="user_role").drop(bind, checkfirst=True)
