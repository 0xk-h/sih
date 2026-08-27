from sqlalchemy import Column, Integer, String
from app.db.base import Base


class Airline(Base):
    __tablename__ = "airlines"

    airline_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    iata_code = Column(String(2), nullable=True)

    def __repr__(self) -> str:
        return f"<Airline {self.iata_code} - {self.name}>"
