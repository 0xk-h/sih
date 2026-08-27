from sqlalchemy import Column, BigInteger, Integer, Numeric, String, Date
from app.db.base import Base


class IndexValue(Base):
    """Published index numbers — national and per-route."""
    __tablename__ = "index_values"

    index_id = Column(BigInteger, primary_key=True, autoincrement=True)
    index_date = Column(Date, nullable=False)
    index_scope = Column(String, nullable=False)   # 'national' | 'route' | 'regional'
    scope_ref = Column(Integer, nullable=True)     # route_id if scope='route', else null
    dtd_bucket = Column(Integer, nullable=True)
    value = Column(Numeric, nullable=False)
    base_period = Column(Date, nullable=True)
    methodology_version = Column(String, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<IndexValue scope={self.index_scope} "
            f"date={self.index_date} value={self.value}>"
        )
