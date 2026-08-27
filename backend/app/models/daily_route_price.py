from sqlalchemy import Column, Integer, Numeric, Date, ForeignKey
from app.db.base import Base


class DailyRoutePrice(Base):
    """Gold layer — daily median representative price per route/dtd_bucket."""
    __tablename__ = "daily_route_price"

    route_id = Column(Integer, ForeignKey("routes.route_id"), primary_key=True)
    price_date = Column(Date, nullable=False, primary_key=True)
    dtd_bucket = Column(Integer, nullable=False, primary_key=True)
    median_fare = Column(Numeric, nullable=True)
    min_fare = Column(Numeric, nullable=True)
    max_fare = Column(Numeric, nullable=True)
    sample_size = Column(Integer, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<DailyRoutePrice route={self.route_id} "
            f"date={self.price_date} dtd={self.dtd_bucket} "
            f"median={self.median_fare}>"
        )
