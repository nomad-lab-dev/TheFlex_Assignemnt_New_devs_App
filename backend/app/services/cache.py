import json
import redis.asyncio as redis
from typing import Dict, Any
import os

# Initialize Redis client (typically configured centrally).
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


async def get_revenue_summary(
    property_id: str,
    tenant_id: str,
    month: int,
    year: int,
) -> Dict[str, Any]:
    """
    Fetches revenue summary for a single month, utilizing caching to improve performance.

    The cache key is scoped by tenant_id AND month/year. Property ids are composite
    with tenant_id in the schema (the same `prop-001` exists for multiple tenants),
    so a tenant-less key would serve one tenant's numbers to another for up to TTL.
    """
    # Scope the cache key per (tenant, property, month) so two tenants or two
    # months never share a Redis slot.
    cache_key = f"revenue:{tenant_id}:{property_id}:{year}-{month:02d}"

    # Try to get from cache
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Revenue calculation is delegated to the reservation service.
    from app.services.reservations import calculate_monthly_revenue

    # Calculate revenue for the requested month in the property's local timezone.
    result = await calculate_monthly_revenue(
        property_id=property_id,
        tenant_id=tenant_id,
        month=month,
        year=year,
    )

    # Cache the result for 5 minutes
    await redis_client.setex(cache_key, 300, json.dumps(result))

    return result
