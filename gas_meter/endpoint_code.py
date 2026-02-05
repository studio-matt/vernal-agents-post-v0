"""
Backend endpoint code for Gas Meter API.

Add this code to your main.py FastAPI application.

Usage in main.py:
    from gas_meter.endpoint_code import router as gas_meter_router
    app.include_router(gas_meter_router)
"""

from fastapi import Depends, APIRouter
from gas_meter.tracker import get_gas_meter_tracker

# Import get_admin_user from auth_api (same as admin routes)
from auth_api import get_admin_user

router = APIRouter()


@router.get("/admin/gas-meter")
async def get_gas_meter_data(admin_user = Depends(get_admin_user)):
    """
    Get current gas meter cost data.
    
    Requires admin authentication.
    
    Returns:
        {
            "llm_tokens_used": int,
            "llm_cost_usd": float,
            "ec2_cost_usd": float,
            "total_cost_usd": float,
            "last_updated": str,
            "session_start": str
        }
    """
    tracker = get_gas_meter_tracker()
    return tracker.get_current_costs()


@router.post("/admin/gas-meter/reset")
async def reset_gas_meter(admin_user = Depends(get_admin_user)):
    """
    Reset gas meter counters (start new session).
    
    Requires admin authentication.
    """
    tracker = get_gas_meter_tracker()
    tracker.reset()
    return {"status": "success", "message": "Gas meter reset successfully"}
