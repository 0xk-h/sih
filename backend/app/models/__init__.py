# Import all models here so Alembic autogenerate can find them
from app.db.base import Base  # noqa: F401
from app.models.airport import Airport  # noqa: F401
from app.models.airline import Airline  # noqa: F401
from app.models.source import Source  # noqa: F401
from app.models.route import Route  # noqa: F401
from app.models.route_weight import RouteWeight  # noqa: F401
from app.models.fare_observation import FareObservation  # noqa: F401
from app.models.daily_route_price import DailyRoutePrice  # noqa: F401
from app.models.index_value import IndexValue  # noqa: F401
