"""
Generation logs API – save and list content/image generation logs per user and campaign.
Requires table: generation_logs (id, user_id, campaign_id, log_text, created_at).
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from auth_api import get_current_user
from database import SessionLocal

logger = logging.getLogger(__name__)

generation_logs_router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SaveLogRequest(BaseModel):
    campaign_id: str
    log_text: str


@generation_logs_router.post("/generation-logs", status_code=201)
async def save_generation_log(
    body: SaveLogRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save one generation log for the current user and campaign. Auth required."""
    if not (body.campaign_id and body.log_text is not None):
        raise HTTPException(status_code=400, detail="campaign_id and log_text are required")
    try:
        db.execute(
            text("""
                INSERT INTO generation_logs (user_id, campaign_id, log_text)
                VALUES (:user_id, :campaign_id, :log_text)
            """),
            {
                "user_id": current_user.id,
                "campaign_id": body.campaign_id,
                "log_text": body.log_text,
            },
        )
        db.commit()
        row = db.execute(
            text("""
                SELECT id, user_id, campaign_id, log_text, created_at
                FROM generation_logs
                WHERE user_id = :user_id AND campaign_id = :campaign_id
                ORDER BY id DESC LIMIT 1
            """),
            {"user_id": current_user.id, "campaign_id": body.campaign_id},
        ).fetchone()
        if row:
            created_at = row[4].isoformat() if hasattr(row[4], "isoformat") else str(row[4])
            return {
                "status": "success",
                "log": {
                    "id": row[0],
                    "user_id": row[1],
                    "campaign_id": row[2],
                    "log_text": row[3],
                    "created_at": created_at,
                },
            }
        return {"status": "success"}
    except Exception as e:
        logger.exception("Failed to save generation log: %s", e)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save log")


@generation_logs_router.get("/generation-logs")
async def list_generation_logs(
    campaign_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List generation logs for the current user, optionally filtered by campaign_id. Newest first."""
    try:
        if campaign_id:
            rows = db.execute(
                text("""
                    SELECT id, user_id, campaign_id, log_text, created_at
                    FROM generation_logs
                    WHERE user_id = :user_id AND campaign_id = :campaign_id
                    ORDER BY created_at DESC
                """),
                {"user_id": current_user.id, "campaign_id": campaign_id},
            ).fetchall()
        else:
            rows = db.execute(
                text("""
                    SELECT id, user_id, campaign_id, log_text, created_at
                    FROM generation_logs
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                """),
                {"user_id": current_user.id},
            ).fetchall()
        logs = []
        for row in rows:
            created_at = row[4].isoformat() if hasattr(row[4], "isoformat") else str(row[4])
            logs.append({
                "id": row[0],
                "user_id": row[1],
                "campaign_id": row[2],
                "log_text": row[3],
                "created_at": created_at,
            })
        return {"status": "success", "logs": logs}
    except Exception as e:
        logger.exception("Failed to list generation logs: %s", e)
        raise HTTPException(status_code=500, detail="Failed to load logs")
