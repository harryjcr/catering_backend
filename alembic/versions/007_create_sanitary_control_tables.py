"""create sanitary control tables

Revision ID: 007_create_sanitary_control_tables
Revises: 006_create_menu_tables
Create Date: 2024-12-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    # =========================
    # sanitary_policies
    # =========================
    op.create_table(
        "sanitary_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
    )

    # =========================
    # sanitary_companies
    # =========================
    op.create_table(
        "sanitary_companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_name", sa.String(length=200), nullable=False),
        sa.Column("ruc", sa.String(length=20), nullable=False, unique=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=150), nullable=True),
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
    )

    # =========================
    # sanitary_incident_types
    # =========================
    op.create_table(
        "sanitary_incident_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
            ["policy_id"],
            ["sanitary_policies.id"],
            name="fk_incident_types_policy_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("policy_id", "name", name="uq_incident_types_policy_name"),
    )

    # Create index for faster lookups by policy
    op.create_index(
        "ix_sanitary_incident_types_policy_id",
        "sanitary_incident_types",
        ["policy_id"],
    )

    # =========================
    # sanitary_reviews
    # =========================
    op.create_table(
        "sanitary_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("is_conform", sa.Boolean(), nullable=False),
        sa.Column("observation", sa.Text(), nullable=True),
        sa.Column("incident_type_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            ["policy_id"],
            ["sanitary_policies.id"],
            name="fk_sanitary_reviews_policy_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_sanitary_reviews_user_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["incident_type_id"],
            ["sanitary_incident_types.id"],
            name="fk_sanitary_reviews_incident_type_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["sanitary_companies.id"],
            name="fk_sanitary_reviews_company_id",
            ondelete="SET NULL",
        ),
    )

    # Create indexes for faster queries
    op.create_index(
        "ix_sanitary_reviews_policy_id",
        "sanitary_reviews",
        ["policy_id"],
    )
    op.create_index(
        "ix_sanitary_reviews_date",
        "sanitary_reviews",
        ["date"],
    )
    op.create_index(
        "ix_sanitary_reviews_user_id",
        "sanitary_reviews",
        ["user_id"],
    )


def downgrade():
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_index("ix_sanitary_reviews_user_id", table_name="sanitary_reviews")
    op.drop_index("ix_sanitary_reviews_date", table_name="sanitary_reviews")
    op.drop_index("ix_sanitary_reviews_policy_id", table_name="sanitary_reviews")
    op.drop_table("sanitary_reviews")

    op.drop_index("ix_sanitary_incident_types_policy_id", table_name="sanitary_incident_types")
    op.drop_table("sanitary_incident_types")

    op.drop_table("sanitary_companies")

    op.drop_table("sanitary_policies")
