from .chat_routes import router as chat_router
from .emergency_routes import router as emergency_router
from .incident_routes import router as incident_router
from .meta_routes import router as meta_router
from .risk_routes import router as risk_router
from .training_routes import router as training_router
from .admin_routes import router as admin_router

__all__ = [
    "chat_router",
    "emergency_router",
    "incident_router",
    "meta_router",
    "risk_router",
    "training_router",
    "admin_router",
]
