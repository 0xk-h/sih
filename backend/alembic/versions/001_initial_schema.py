"""Initial schema: all 8 tables per DEVELOPMENT.md §5

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── airports ────────────────────────────────────────────────────────────
    op.create_table(
        "airports",
        sa.Column("airport_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("iata_code", sa.String(3), nullable=False),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("airport_id"),
        sa.UniqueConstraint("iata_code"),
    )

    # ── airlines ────────────────────────────────────────────────────────────
    op.create_table(
        "airlines",
        sa.Column("airline_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("iata_code", sa.String(2), nullable=True),
        sa.PrimaryKeyConstraint("airline_id"),
    )

    # ── sources ─────────────────────────────────────────────────────────────
    op.create_table(
        "sources",
        sa.Column("source_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("source_id"),
    )

    # ── routes ──────────────────────────────────────────────────────────────
    op.create_table(
        "routes",
        sa.Column("route_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("origin_airport_id", sa.Integer(), nullable=False),
        sa.Column("dest_airport_id", sa.Integer(), nullable=False),
        sa.Column("distance_km", sa.Numeric(), nullable=True),
        sa.ForeignKeyConstraint(["origin_airport_id"], ["airports.airport_id"]),
        sa.ForeignKeyConstraint(["dest_airport_id"], ["airports.airport_id"]),
        sa.PrimaryKeyConstraint("route_id"),
    )

    # ── route_weights ────────────────────────────────────────────────────────
    op.create_table(
        "route_weights",
        sa.Column("route_id", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Numeric(), nullable=False),
        sa.Column("weight_source", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["route_id"], ["routes.route_id"]),
        sa.PrimaryKeyConstraint("route_id", "effective_from"),
    )

    # ── fare_observations ────────────────────────────────────────────────────
    op.create_table(
        "fare_observations",
        sa.Column("obs_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("route_id", sa.Integer(), nullable=False),
        sa.Column("airline_id", sa.Integer(), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("departure_date", sa.Date(), nullable=False),
        sa.Column("days_to_departure", sa.Integer(), nullable=False),
        sa.Column("dtd_bucket", sa.Integer(), nullable=False),
        sa.Column("fare_class", sa.Text(), nullable=True),
        sa.Column("base_fare", sa.Numeric(), nullable=True),
        sa.Column("taxes_fees", sa.Numeric(), nullable=True),
        sa.Column("total_fare", sa.Numeric(), nullable=False),
        sa.Column("currency", sa.String(3), server_default="INR"),
        sa.Column("collected_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("scrape_batch_id", UUID(as_uuid=True), nullable=True),
        sa.Column("raw_snapshot_ref", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["route_id"], ["routes.route_id"]),
        sa.ForeignKeyConstraint(["airline_id"], ["airlines.airline_id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.source_id"]),
        sa.PrimaryKeyConstraint("obs_id"),
        sa.UniqueConstraint(
            "route_id", "airline_id", "source_id",
            "departure_date", "dtd_bucket", "fare_class",
            name="uq_fare_observation_dedup",
        ),
    )
    op.create_index(
        "ix_fare_obs_route_dtd_date",
        "fare_observations",
        ["route_id", "dtd_bucket", "departure_date"],
    )
    op.create_index(
        "ix_fare_obs_collected_at",
        "fare_observations",
        ["collected_at"],
    )

    # ── daily_route_price ────────────────────────────────────────────────────
    op.create_table(
        "daily_route_price",
        sa.Column("route_id", sa.Integer(), nullable=False),
        sa.Column("price_date", sa.Date(), nullable=False),
        sa.Column("dtd_bucket", sa.Integer(), nullable=False),
        sa.Column("median_fare", sa.Numeric(), nullable=True),
        sa.Column("min_fare", sa.Numeric(), nullable=True),
        sa.Column("max_fare", sa.Numeric(), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["route_id"], ["routes.route_id"]),
        sa.PrimaryKeyConstraint("route_id", "price_date", "dtd_bucket"),
    )

    # ── index_values ─────────────────────────────────────────────────────────
    op.create_table(
        "index_values",
        sa.Column("index_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("index_date", sa.Date(), nullable=False),
        sa.Column("index_scope", sa.Text(), nullable=False),
        sa.Column("scope_ref", sa.Integer(), nullable=True),
        sa.Column("dtd_bucket", sa.Integer(), nullable=True),
        sa.Column("value", sa.Numeric(), nullable=False),
        sa.Column("base_period", sa.Date(), nullable=True),
        sa.Column("methodology_version", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("index_id"),
    )
    op.create_index(
        "ix_index_values_scope_date",
        "index_values",
        ["index_scope", "scope_ref", "index_date", "dtd_bucket"],
    )


def downgrade() -> None:
    op.drop_table("index_values")
    op.drop_table("daily_route_price")
    op.drop_table("fare_observations")
    op.drop_table("route_weights")
    op.drop_table("routes")
    op.drop_table("sources")
    op.drop_table("airlines")
    op.drop_table("airports")
