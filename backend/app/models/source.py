from sqlalchemy import Column, Integer, String
from app.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    source_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)          # e.g. 'MakeMyTrip', 'IndiGo Direct'
    source_type = Column(String, nullable=False)   # 'airline_direct' | 'ota'
    base_url = Column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<Source {self.name} ({self.source_type})>"
