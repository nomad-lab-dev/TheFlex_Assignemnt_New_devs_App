from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from app.services.cache import get_revenue_summary
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:

    tenant_id = getattr(current_user, "tenant_id", "default_tenant") or "default_tenant"

    # Default to current month/year if not supplied.
    now = datetime.utcnow()
    resolved_month = month or now.month
    resolved_year = year or now.year

    revenue_data = await get_revenue_summary(
        property_id=property_id,
        tenant_id=tenant_id,
        month=resolved_month,
        year=resolved_year,
    )

    # Keep Decimal precision; quantize to 2 decimals (ROUND_HALF_UP) and serialize as string
    total_decimal = Decimal(str(revenue_data["total"])).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return {
        "property_id": revenue_data["property_id"],
        "month": revenue_data["month"],
        "year": revenue_data["year"],
        "timezone": revenue_data.get("timezone", "UTC"),
        "total_revenue": str(total_decimal),
        "currency": revenue_data["currency"],
        "reservations_count": revenue_data["count"],
        "reservations": revenue_data.get("reservations", []),
    }
