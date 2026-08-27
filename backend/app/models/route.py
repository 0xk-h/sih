from sqlalchemy import Column, Integer, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class Route(Base):
    __tablename__ = "routes"

    route_id = Column(Integer, primary_key=True, autoincrement=True)
    origin_airport_id = Column(Integer, ForeignKey("airports.airport_id"), nullable=False)
    dest_airport_id = Column(Integer, ForeignKey("airports.airport_id"), nullable=False)
    distance_km = Column(Numeric, nullable=True)

    origin = relationship("Airport", foreign_keys=[origin_airport_id])
    destination = relationship("Airport", foreign_keys=[dest_airport_id])
    weights = relationship("RouteWeight", back_populates="route")

    def __repr__(self) -> str:
        return f"<Route {self.route_id}>"
