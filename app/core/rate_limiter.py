from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])

# Stricter per-route limits, on top of the default above.
# Password endpoints: slow down credential stuffing and sign-up spam.
AUTH_LIMIT = "10/minute"
AUTH_REFRESH_LIMIT = "30/minute"
# Endpoints that call OpenAI: each request costs money, so cap them per client.
AI_LIMIT = "20/minute"
