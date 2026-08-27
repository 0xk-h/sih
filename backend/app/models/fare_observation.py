from sqlalchemy import (
    Column, BigInteger, Integer, Numeric, String, Date, ForeignKey,
    TIMESTAMP, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class FareObservation(Base):
    """
    Silver layer — cleaned, normalized fare observations.
    Every row MUST carry collected_at and dtd_bucket per spec Section 5.
    """
    __tablename__ = "fare_observations"

    obs_id = Column(BigInteger, primary_key=True, autoincrement=True)
    route_id = Column(Integer, ForeignKey("routes.route_id"), nullable=False)
    airline_id = Column(Integer, ForeignKey("airlines.airline_id"), nullable=True)
    source_id = Column(Integer, ForeignKey("sources.source_id"), nullable=False)
    departure_date = Column(Date, nullable=False)
    days_to_departure = Column(Integer, nullable=False)
    dtd_bucket = Column(Integer, nullable=False)            # snapped to 14 or 1 (MVP scope)
    fare_class = Column(String, nullable=True)              # 'economy' | 'premium_economy' | 'business'
    base_fare = Column(Numeric, nullable=True)
    taxes_fees = Column(Numeric, nullable=True)
    total_fare = Column(Numeric, nullable=False)
    currency = Column(String(3), default="INR")
    collected_at = Column(TIMESTAMP(timezone=True), nullable=False)
    scrape_batch_id = Column(UUID(as_uuid=True), nullable=True)
    raw_snapshot_ref = Column(String, nullable=True)       # pointer to bronze record for audit

    # Dedup constraint per spec §5:
    # (route, airline, source, departure_date, dtd_bucket, fare_class, hour(collected_at))
    __table_args__ = (
        UniqueConstraint(
            "route_id", "airline_id", "source_id",
            "departure_date", "dtd_bucket", "fare_class",
            name="uq_fare_observation_dedup",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<FareObservation route={self.route_id} "
            f"dtd={self.dtd_bucket} fare={self.total_fare} "
            f"at={self.collected_at}>"
        )
