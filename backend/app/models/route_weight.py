from sqlalchemy import Column, Integer, Numeric, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class RouteWeight(Base):
    __tablename__ = "route_weights"

    route_id = Column(Integer, ForeignKey("routes.route_id"), primary_key=True)
    effective_from = Column(Date, primary_key=True)
    weight = Column(Numeric, nullable=False)       # basket weight, sums to 1 across active routes
    weight_source = Column(String, nullable=True)  # e.g. 'DGCA FY25 traffic share'

    route = relationship("Route", back_populates="weights")

    def __repr__(self) -> str:
        return f"<RouteWeight route_id={self.route_id} weight={self.weight}>"
