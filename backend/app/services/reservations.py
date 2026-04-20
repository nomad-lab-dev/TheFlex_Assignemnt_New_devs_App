import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from zoneinfo import ZoneInfo

import asyncpg

_DB_POOL: Optional[asyncpg.Pool] = None


async def _get_pool() -> asyncpg.Pool:
    """Lazy asyncpg pool against the Postgres container from docker-compose."""
    global _DB_POOL
    if _DB_POOL is None:
        dsn = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@db:5432/propertyflow",
        )
        _DB_POOL = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5)
    return _DB_POOL


async def _get_property_timezone(
    conn: asyncpg.Connection, property_id: str, tenant_id: str
) -> str:
    row = await conn.fetchrow(
        "SELECT timezone FROM properties WHERE id = $1 AND tenant_id = $2",
        property_id,
        tenant_id,
    )
    return row["timezone"] if row and row["timezone"] else "UTC"


async def calculate_monthly_revenue(
    property_id: str,
    tenant_id: str,
    month: int,
    year: int,
) -> Dict[str, Any]:
    """Sum revenue for a single calendar month in the property's local timezone."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        tz_name = await _get_property_timezone(conn, property_id, tenant_id)
        tz = ZoneInfo(tz_name)

        # Month boundaries in the property's local tz; Postgres handles the UTC comparison.
        start_local = datetime(year, month, 1, tzinfo=tz)
        end_local = datetime(year + (month // 12), (month % 12) + 1, 1, tzinfo=tz)

        reservations = await conn.fetch(
            """
            SELECT id, check_in_date, check_out_date, total_amount, currency
            FROM reservations
            WHERE property_id = $1
              AND tenant_id = $2
              AND check_in_date >= $3
              AND check_in_date <  $4
            ORDER BY check_in_date ASC
            """,
            property_id,
            tenant_id,
            start_local,
            end_local,
        )

    total = sum(
        (Decimal(str(r["total_amount"])) for r in reservations),
        Decimal(0),
    )

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
                "check_in": r["check_in_date"].astimezone(tz).isoformat(),
                "check_out": r["check_out_date"].astimezone(tz).isoformat(),
                "amount": str(Decimal(str(r["total_amount"]))),
                "currency": r["currency"] or "USD",
            }
            for r in reservations
        ],
    }
