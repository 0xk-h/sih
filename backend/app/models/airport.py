from sqlalchemy import Column, Integer, String, Numeric
from app.db.base import Base


class Airport(Base):
    __tablename__ = "airports"

    airport_id = Column(Integer, primary_key=True, autoincrement=True)
    iata_code = Column(String(3), unique=True, nullable=False)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<Airport {self.iata_code} - {self.city}>"
