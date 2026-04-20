import os
from decimal import Decimal
from typing import Dict, Any, Optional

import asyncpg

# Module-level pool, lazily created on first use.
_DB_POOL: Optional[asyncpg.Pool] = None


async def _get_pool() -> asyncpg.Pool:
    """Lazy asyncpg pool against the Postgres container from docker-compose."""
    global _DB_POOL
    if _DB_POOL is None:
        # DATABASE_URL is set in docker-compose; fall back to the container alias for local dev.
        dsn = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@db:5432/propertyflow",
        )
        _DB_POOL = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5)
    return _DB_POOL


async def calculate_monthly_revenue(
    property_id: str,
    tenant_id: str,
    month: int,
    year: int,
) -> Dict[str, Any]:
    """
    Sum revenue for a calendar month in the property's local timezone.

    The tz math runs in Postgres via `AT TIME ZONE`: check_in_date is converted
    from TIMESTAMPTZ to wall-clock time in the property's zone, then compared
    against naive local month bounds. Postgres handles DST transitions for us.
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        # Pull the property's timezone so the UI can render dates in that zone
        # and so we can pass it to the monthly query below.
        tz_row = await conn.fetchrow(
            "SELECT timezone FROM properties WHERE id = $1 AND tenant_id = $2",
            property_id,
            tenant_id,
        )
        tz_name = (tz_row and tz_row["timezone"]) or "UTC"

        # AT TIME ZONE $5 shifts the TIMESTAMPTZ into the property's wall-clock,
        # which we then compare to the naive local month window.
        reservations = await conn.fetch(
            """
            SELECT id, check_in_date, check_out_date, total_amount, currency
            FROM reservations
            WHERE property_id = $1
              AND tenant_id = $2
              AND (check_in_date AT TIME ZONE $5) >= make_date($3, $4, 1)
              AND (check_in_date AT TIME ZONE $5) <  make_date($3, $4, 1) + INTERVAL '1 month'
            ORDER BY check_in_date ASC
            """,
            property_id,
            tenant_id,
            year,
            month,
            tz_name,
        )

    # Keep everything in Decimal. Any cast to float here would reintroduce the
    # sub-cent drift that NUMERIC(10, 3) is explicitly designed to avoid.
    total = sum(
        (Decimal(str(r["total_amount"])) for r in reservations),
        Decimal(0),
    )

    # Dates are returned as raw UTC ISO strings; the frontend renders them in
    # `tz_name` using Intl.DateTimeFormat({ timeZone }).
    return {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "month": month,
        "year": year,
        "timezone": tz_name,
        "total": str(total),
        "currency": "USD",
        "count": len(reservations),
        "reservations": [
            {
                "id": r["id"],
                "check_in": r["check_in_date"].isoformat(),
                "check_out": r["check_out_date"].isoformat(),
                "amount": str(Decimal(str(r["total_amount"]))),
                "currency": r["currency"] or "USD",
            }
            for r in reservations
        ],
    }
