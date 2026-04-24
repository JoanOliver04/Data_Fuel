"""Global rate limiter using slowapi (keyed by client IP).

Wiring lives in ``app.main.create_app``; endpoints apply limits via
``@limiter.limit(...)`` and must accept ``request: Request`` as a parameter.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
