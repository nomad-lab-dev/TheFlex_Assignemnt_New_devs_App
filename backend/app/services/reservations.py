import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
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


async def _get_property_timezone(property_id: str, tenant_id: str) -> str:
    pool = await _get_pool()
    async with pool.acquire() as conn:
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
    tz_name = await _get_property_timezone(property_id, tenant_id)
    tz = ZoneInfo(tz_name)

    # Month boundaries expressed in the property's local tz, converted to UTC for the query.
    start_local = datetime(year, month, 1, tzinfo=tz)
    if month < 12:
        end_local = datetime(year, month + 1, 1, tzinfo=tz)
    else:
        end_local = datetime(year + 1, 1, 1, tzinfo=tz)

    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                COALESCE(SUM(total_amount), 0) AS total,
                COUNT(*) AS count
            FROM reservations
            WHERE property_id = $1
              AND tenant_id = $2
              AND check_in_date >= $3
              AND check_in_date <  $4
            """,
            property_id,
            tenant_id,
            start_local,
            end_local,
        )
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

    total = Decimal(str(row["total"]))

    return {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "month": month,
        "year": year,
        "timezone": tz_name,
        "total": str(total),
        "currency": "USD",
        "count": row["count"],
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


async def calculate_total_revenue(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """Backward-compatible wrapper: defaults to March 2026 (current seed period)."""
    default_year = int(os.getenv("REVENUE_DEFAULT_YEAR", "2026"))
    default_month = int(os.getenv("REVENUE_DEFAULT_MONTH", "3"))
    return await calculate_monthly_revenue(
        property_id=property_id,
        tenant_id=tenant_id,
        month=default_month,
        year=default_year,
    )
