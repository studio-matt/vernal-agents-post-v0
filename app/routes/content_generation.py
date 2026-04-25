"""
Content generation, scheduling, and image endpoints extracted from main.py
Moved from main.py to preserve API contract parity
"""
import logging
import json
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from fastapi import APIRouter, HTTPException, Depends, status, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from auth_api import get_current_user
from database import SessionLocal
from openai_model_config import get_openai_default_model

logger = logging.getLogger(__name__)

content_generation_router = APIRouter()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Import shared utilities from main (TODO: move to app/utils in future refactor)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.utils.openai_helpers import get_openai_api_key
from app.utils.content_tasks import CONTENT_GEN_TASKS, CONTENT_GEN_TASK_INDEX, MAX_CONTENT_GEN_DURATION_SEC
from app.schemas.models import AnalyzeRequest

DAY_ORDER = {
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
    "sunday": 7,
}


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _task_index_add(campaign_id: str, task_id: str) -> None:
    existing = CONTENT_GEN_TASK_INDEX.get(campaign_id)
    if isinstance(existing, list):
        if task_id not in existing:
            existing.insert(0, task_id)
    elif existing:
        CONTENT_GEN_TASK_INDEX[campaign_id] = [task_id, existing]
    else:
        CONTENT_GEN_TASK_INDEX[campaign_id] = [task_id]


def _task_index_remove(campaign_id: str, task_id: str) -> None:
    existing = CONTENT_GEN_TASK_INDEX.get(campaign_id)
    if isinstance(existing, list):
        CONTENT_GEN_TASK_INDEX[campaign_id] = [tid for tid in existing if tid != task_id]
    elif existing == task_id:
        CONTENT_GEN_TASK_INDEX.pop(campaign_id, None)


def _set_content_task(task_id: str, **updates: Any) -> None:
    task = CONTENT_GEN_TASKS.get(task_id)
    if not task:
        return
    task.update(updates)
    task["updated_at"] = _now_iso()


def _task_progress_from_steps(task: Dict[str, Any]) -> int:
    steps = task.get("steps") or []
    if not steps:
        return int(task.get("progress") or 0)
    total = max(1, len(steps))
    progress = 10
    for idx, step in enumerate(steps):
        status_value = step.get("status")
        phase = step.get("phase")
        base = int((idx / total) * 100)
        span = max(1, int(100 / total))
        if status_value == "completed":
            progress = max(progress, min(99, base + span))
        elif status_value == "error":
            progress = max(progress, min(99, base + max(1, span // 2)))
        elif status_value == "running":
            if phase == "copy":
                progress = max(progress, min(45, base + max(10, span // 4)))
            elif phase == "image":
                progress = max(progress, min(90, base + 5))
            else:
                progress = max(progress, min(90, base + max(5, span // 2)))
        elif status_value == "pending":
            progress = max(progress, min(95, base))
            break
    if task.get("status") == "completed":
        return 100
    return max(1, min(99, progress))


def _set_step_status(task_id: str, step_id: str, status_value: str, **updates: Any) -> None:
    task = CONTENT_GEN_TASKS.get(task_id)
    if not task:
        return
    for step in task.get("steps", []):
        if step.get("id") == step_id:
            step.update(updates)
            step["status"] = status_value
            step["updated_at"] = _now_iso()
            break
    task["agent_statuses"] = [
        {
            "agent": step.get("agent", "Content Generation"),
            "task": step.get("label", ""),
            "status": step.get("status", "pending"),
            "timestamp": step.get("updated_at") or task.get("updated_at"),
            "error": step.get("error"),
            "content_item_id": step.get("content_item_id"),
            "database_id": step.get("database_id"),
            "image_url": step.get("image_url"),
        }
        for step in task.get("steps", [])
    ]
    task["progress"] = _task_progress_from_steps(task)
    task["updated_at"] = _now_iso()


def _normalize_generation_item(raw: Dict[str, Any], index: int) -> Dict[str, Any]:
    platform = (raw.get("platform") or "linkedin").lower()
    week = int(raw.get("week") or 1)
    day = raw.get("day") or "Monday"
    item_type = (raw.get("type") or "secondary").lower()
    if item_type not in {"cornerstone", "secondary"}:
        item_type = "secondary"
    content_item_id = raw.get("content_item_id", raw.get("contentItemId", raw.get("id")))
    return {
        "content_item_id": content_item_id,
        "platform": platform,
        "week": week,
        "day": day,
        "type": item_type,
        "title": raw.get("title") or raw.get("parent_idea") or raw.get("parentIdea") or f"{platform.title()} content",
        "parent_idea": raw.get("parent_idea") or raw.get("parentIdea") or raw.get("title") or "",
        "content_queue_items": raw.get("content_queue_items") or raw.get("contentQueueItems") or [],
        "generate_image": raw.get("generate_image", raw.get("generateImage", True)) is not False,
        "_input_index": index,
    }


def _ordered_generation_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            int(item.get("week") or 1),
            DAY_ORDER.get(str(item.get("day") or "Monday").lower(), 99),
            str(item.get("day") or "Monday"),
            0 if item.get("type") == "cornerstone" else 1,
            item.get("_input_index", 0),
        ),
    )


def _build_steps(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    for idx, item in enumerate(items):
        label_prefix = "Cornerstone" if item["type"] == "cornerstone" else "Secondary"
        title = item.get("title") or item["platform"].title()
        copy_id = f"{idx}-copy"
        image_id = f"{idx}-image"
        steps.append({
            "id": copy_id,
            "phase": "copy",
            "agent": "Content Generation",
            "label": f"{label_prefix} copy: {title}",
            "status": "pending",
            "content_item_id": item.get("content_item_id"),
            "platform": item.get("platform"),
            "week": item.get("week"),
            "day": item.get("day"),
        })
        if item.get("generate_image") is not False:
            steps.append({
                "id": image_id,
                "phase": "image",
                "agent": "Image Generation",
                "label": f"{label_prefix} image: {title}",
                "status": "pending",
                "content_item_id": item.get("content_item_id"),
                "platform": item.get("platform"),
                "week": item.get("week"),
                "day": item.get("day"),
            })
    return steps


def _create_generation_task(
    *,
    campaign_id: str,
    user_id: int,
    scope: str,
    items: List[Dict[str, Any]],
    week: Optional[int] = None,
    day: Optional[str] = None,
    author_personality_id: Optional[str] = None,
    brand_personality_id: Optional[str] = None,
    platform_settings: Optional[Dict[str, Any]] = None,
    image_settings: Optional[Dict[str, Any]] = None,
) -> str:
    task_id = f"content-{uuid.uuid4()}"
    ordered = _ordered_generation_items(items)
    CONTENT_GEN_TASKS[task_id] = {
        "task_id": task_id,
        "campaign_id": campaign_id,
        "user_id": user_id,
        "scope": scope,
        "week": week,
        "day": day,
        "status": "pending",
        "progress": 0,
        "current_agent": "Content Generation",
        "current_task": "Queued content generation",
        "agent_statuses": [],
        "steps": _build_steps(ordered),
        "items": ordered,
        "items_done": 0,
        "items_total": len(ordered),
        "result": None,
        "error": None,
        "author_personality_id": author_personality_id,
        "brand_personality_id": brand_personality_id,
        "platform_settings": platform_settings or {},
        "image_settings": image_settings,
        "started_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    _task_index_add(campaign_id, task_id)
    return task_id


def _verify_campaign_access(campaign_id: str, current_user: Any, db: Session):
    from models import Campaign
    query = db.query(Campaign).filter(Campaign.campaign_id == campaign_id)
    if not getattr(current_user, "is_admin", False):
        query = query.filter(Campaign.user_id == current_user.id)
    campaign = query.first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found or access denied")
    return campaign


def _content_source_text(campaign: Any, item: Dict[str, Any], cornerstone_content: Optional[str]) -> str:
    queue_items = item.get("content_queue_items") or []
    queue_text = "\n".join(
        str(q.get("text") or q.get("name") or q.get("title") or q)
        for q in queue_items
        if q
    ).strip()
    campaign_context = "\n".join(
        str(value)
        for value in [
            getattr(campaign, "campaign_name", ""),
            getattr(campaign, "description", ""),
            getattr(campaign, "query", ""),
            getattr(campaign, "keywords", ""),
            getattr(campaign, "topics", ""),
        ]
        if value
    ).strip()
    parts = [
        f"Title/idea: {item.get('title') or item.get('parent_idea') or ''}",
        f"Campaign context: {campaign_context}",
    ]
    if queue_text:
        parts.append(f"Selected research/content queue inputs:\n{queue_text}")
    if cornerstone_content:
        parts.append(f"Cornerstone content to reference:\n{cornerstone_content}")
    return "\n\n".join(parts)


def _generate_copy(
    *,
    db: Session,
    user: Any,
    campaign: Any,
    item: Dict[str, Any],
    cornerstone_content: Optional[str],
) -> Dict[str, Any]:
    from langchain_openai import ChatOpenAI
    api_key = get_openai_api_key(current_user=user, db=db)
    if not api_key:
        raise ValueError("OpenAI API key is not configured.")

    platform = item["platform"]
    item_type = item["type"]
    source_text = _content_source_text(campaign, item, cornerstone_content)
    if item_type == "secondary" and not cornerstone_content:
        source_text += "\n\nNo cornerstone copy was available; write the best standalone secondary content possible."

    prompt = f"""You are generating production-ready campaign content.

Platform: {platform}
Content type: {item_type}
Week: {item.get('week')}
Day: {item.get('day')}

Requirements:
- Write only the final content, with no preamble.
- Respect the platform format.
- If this is secondary content, support and reference the cornerstone direction without repeating it verbatim.
- If this is WordPress, include a strong article body with useful structure.

Inputs:
{source_text}
"""
    llm = ChatOpenAI(model=get_openai_default_model(), api_key=api_key.strip(), temperature=0.7)
    response = llm.invoke(prompt)
    content = (getattr(response, "content", "") or "").strip()
    if not content:
        raise ValueError("Generated content was empty.")

    title = item.get("title") or content.splitlines()[0][:80] or f"{platform.title()} content"
    data = {
        "title": title,
        "content": content,
        "platform_content": {"title": title, "content": content},
        "content_item_id": item.get("content_item_id"),
    }
    if platform == "wordpress":
        slug = "-".join(title.lower().split())[:80]
        data.update({
            "post_title": title,
            "post_excerpt": content[:240],
            "permalink": slug,
        })
    return data


def _lookup_cornerstone_content(db: Session, campaign_id: str, user_id: int, week: int, day: str, exclude_platform: str) -> Optional[str]:
    row = db.execute(text("""
        SELECT content
        FROM content
        WHERE campaign_id = :campaign_id
          AND user_id = :user_id
          AND week = :week
          AND day = :day
          AND platform != :platform
          AND content IS NOT NULL
          AND TRIM(content) != ''
        ORDER BY id ASC
        LIMIT 1
    """), {
        "campaign_id": campaign_id,
        "user_id": user_id,
        "week": week,
        "day": day,
        "platform": exclude_platform,
    }).first()
    return row[0] if row else None


def _upsert_generated_content(
    db: Session,
    *,
    campaign_id: str,
    user_id: int,
    item: Dict[str, Any],
    copy_data: Dict[str, Any],
    image_url: Optional[str] = None,
) -> int:
    content_item_id = item.get("content_item_id")
    platform = (item.get("platform") or "linkedin").lower()
    week = int(item.get("week") or 1)
    day = item.get("day") or "Monday"
    now = datetime.utcnow()

    existing_id: Optional[int] = None
    if content_item_id is not None and str(content_item_id).isdigit():
        row = db.execute(text("""
            SELECT id FROM content
            WHERE id = :id AND campaign_id = :campaign_id AND user_id = :user_id
            LIMIT 1
        """), {"id": int(content_item_id), "campaign_id": campaign_id, "user_id": user_id}).first()
        if row:
            existing_id = int(row[0])

    if existing_id is None:
        row = db.execute(text("""
            SELECT id FROM content
            WHERE campaign_id = :campaign_id AND user_id = :user_id AND week = :week AND day = :day AND platform = :platform
            LIMIT 1
        """), {
            "campaign_id": campaign_id,
            "user_id": user_id,
            "week": week,
            "day": day,
            "platform": platform,
        }).first()
        if row:
            existing_id = int(row[0])

    values = {
        "user_id": user_id,
        "campaign_id": campaign_id,
        "week": week,
        "day": day,
        "platform": platform,
        "content": copy_data.get("content") or "",
        "title": copy_data.get("title") or item.get("title") or f"{platform.title()} content",
        "image_url": image_url,
        "date_upload": now,
        "schedule_time": now.replace(hour=9, minute=0, second=0, microsecond=0),
        "file_name": f"{platform}_{week}_{day}.txt",
        "file_type": "text",
        "platform_post_no": "1",
        "status": "draft",
        "is_draft": True,
        "can_edit": True,
        "parent_idea": item.get("parent_idea") or item.get("title") or "",
        "post_title": copy_data.get("post_title"),
        "post_excerpt": copy_data.get("post_excerpt"),
        "permalink": copy_data.get("permalink"),
    }

    if existing_id is not None:
        values["id"] = existing_id
        db.execute(text("""
            UPDATE content
            SET title = :title,
                content = :content,
                image_url = COALESCE(:image_url, image_url),
                status = :status,
                is_draft = :is_draft,
                can_edit = :can_edit,
                parent_idea = :parent_idea,
                post_title = :post_title,
                post_excerpt = :post_excerpt,
                permalink = :permalink
            WHERE id = :id
        """), values)
        db.commit()
        return existing_id

    result = db.execute(text("""
        INSERT INTO content (
            user_id, campaign_id, week, day, platform, content, title, status,
            date_upload, schedule_time, file_name, file_type, platform_post_no,
            image_url, is_draft, can_edit, parent_idea, post_title, post_excerpt, permalink
        ) VALUES (
            :user_id, :campaign_id, :week, :day, :platform, :content, :title, :status,
            :date_upload, :schedule_time, :file_name, :file_type, :platform_post_no,
            :image_url, :is_draft, :can_edit, :parent_idea, :post_title, :post_excerpt, :permalink
        )
    """), values)
    db.commit()
    return int(result.lastrowid)


def _generate_image_for_copy(db: Session, user: Any, copy_text: str, image_settings: Optional[Dict[str, Any]]) -> str:
    from tools import generate_image
    api_key = get_openai_api_key(current_user=user, db=db)
    if not api_key:
        raise ValueError("OpenAI API key is not configured.")
    article_summary = copy_text[:500]
    style_parts: List[str] = []
    if image_settings:
        if image_settings.get("style"):
            style_parts.append(f"in {image_settings.get('style')} style")
        if image_settings.get("color"):
            style_parts.append(f"with {image_settings.get('color')} color palette")
        if image_settings.get("prompt") or image_settings.get("additionalPrompt"):
            style_parts.append(str(image_settings.get("prompt") or image_settings.get("additionalPrompt")))
    final_prompt = article_summary
    if style_parts:
        final_prompt += "\n\nCreative direction: " + ", ".join(style_parts)
    return generate_image(query=copy_text, content=final_prompt, api_key=api_key)


def _save_backend_generation_log(db: Session, task: Dict[str, Any]) -> None:
    """Persist a backend-owned generation task log without requiring the modal to open."""
    try:
        steps = task.get("steps", [])
        step_lines = "\n".join(
            "- {label}: {status}{db}{image}{error}".format(
                label=step.get("label"),
                status=step.get("status"),
                db=f" db={step.get('database_id')}" if step.get("database_id") else "",
                image=f" image={step.get('image_url')}" if step.get("image_url") else "",
                error=f" error={step.get('error')}" if step.get("error") else "",
            )
            for step in steps
        )
        result = task.get("result") or {}
        log_text = (
            "Backend Content Generation Log\n"
            "============================================================\n"
            f"Task ID: {task.get('task_id')}\n"
            f"Campaign ID: {task.get('campaign_id')}\n"
            f"Scope: {task.get('scope')}\n"
            f"Status: {task.get('status')}\n"
            f"Progress: {task.get('progress')}%\n"
            f"Items: {task.get('items_done')} / {task.get('items_total')}\n"
            f"Error: {task.get('error') or ''}\n\n"
            "Steps:\n"
            f"{step_lines}\n\n"
            "Result:\n"
            f"{json.dumps(result, default=str)[:8000]}\n"
        )
        db.execute(text("""
            INSERT INTO generation_logs (user_id, campaign_id, log_text)
            VALUES (:user_id, :campaign_id, :log_text)
        """), {
            "user_id": task.get("user_id"),
            "campaign_id": task.get("campaign_id"),
            "log_text": log_text,
        })
        db.commit()
    except Exception:
        logger.exception("Failed to persist backend generation log for task %s", task.get("task_id"))
        db.rollback()


def _run_generation_task(task_id: str) -> None:
    task = CONTENT_GEN_TASKS.get(task_id)
    if not task:
        return

    db = SessionLocal()
    try:
        from models import Campaign, User
        user = db.query(User).filter(User.id == task["user_id"]).first()
        campaign = db.query(Campaign).filter(Campaign.campaign_id == task["campaign_id"]).first()
        if not user or not campaign:
            raise ValueError("Campaign or user was not found for generation task.")

        _set_content_task(task_id, status="in_progress", current_task="Starting content generation", progress=10)
        generated_cornerstones: Dict[Tuple[int, str], str] = {}
        results: List[Dict[str, Any]] = []

        for idx, item in enumerate(task.get("items", [])):
            copy_step_id = f"{idx}-copy"
            image_step_id = f"{idx}-image"
            day_key = (int(item.get("week") or 1), item.get("day") or "Monday")
            cornerstone_content = generated_cornerstones.get(day_key)
            if item.get("type") == "secondary" and not cornerstone_content:
                cornerstone_content = _lookup_cornerstone_content(
                    db,
                    task["campaign_id"],
                    task["user_id"],
                    day_key[0],
                    day_key[1],
                    item.get("platform") or "",
                )

            _set_step_status(task_id, copy_step_id, "running")
            _set_content_task(
                task_id,
                current_agent="Content Generation",
                current_task=f"Generating {'cornerstone' if item.get('type') == 'cornerstone' else 'secondary'} copy {idx + 1} of {len(task.get('items', []))}",
            )
            copy_data = _generate_copy(db=db, user=user, campaign=campaign, item=item, cornerstone_content=cornerstone_content)
            database_id = _upsert_generated_content(
                db,
                campaign_id=task["campaign_id"],
                user_id=task["user_id"],
                item=item,
                copy_data=copy_data,
                image_url=None,
            )
            if item.get("type") == "cornerstone":
                generated_cornerstones[day_key] = copy_data["content"]

            _set_step_status(task_id, copy_step_id, "completed", database_id=database_id)
            _set_content_task(
                task_id,
                result={"status": "success", "data": {**copy_data, "id": database_id, "database_id": database_id, "content_item_id": item.get("content_item_id")}},
            )

            image_url = None
            if item.get("generate_image") is not False:
                _set_step_status(task_id, image_step_id, "running", database_id=database_id)
                _set_content_task(
                    task_id,
                    current_agent="Image Generation",
                    current_task=f"Generating image {idx + 1} of {len(task.get('items', []))}",
                )
                try:
                    image_url = _generate_image_for_copy(db, user, copy_data["content"], task.get("image_settings"))
                    database_id = _upsert_generated_content(
                        db,
                        campaign_id=task["campaign_id"],
                        user_id=task["user_id"],
                        item={**item, "content_item_id": database_id},
                        copy_data=copy_data,
                        image_url=image_url,
                    )
                    _set_step_status(task_id, image_step_id, "completed", database_id=database_id, image_url=image_url)
                except Exception as image_exc:
                    image_error = str(image_exc)
                    _set_step_status(task_id, image_step_id, "error", database_id=database_id, error=image_error)
                    results.append({
                        **copy_data,
                        "id": database_id,
                        "database_id": database_id,
                        "content_item_id": item.get("content_item_id"),
                        "image_url": None,
                        "platform": item.get("platform"),
                        "week": item.get("week"),
                        "day": item.get("day"),
                        "type": item.get("type"),
                    })
                    _set_content_task(
                        task_id,
                        status="error",
                        error=image_error,
                        current_agent=None,
                        current_task="Image generation failed",
                        items_done=len(results),
                        result={"status": "error", "error": image_error, "data": results[-1], "items": results},
                    )
                    _save_backend_generation_log(db, CONTENT_GEN_TASKS.get(task_id, task))
                    return

            results.append({
                **copy_data,
                "id": database_id,
                "database_id": database_id,
                "content_item_id": item.get("content_item_id"),
                "image_url": image_url,
                "platform": item.get("platform"),
                "week": item.get("week"),
                "day": item.get("day"),
                "type": item.get("type"),
            })
            _set_content_task(
                task_id,
                items_done=len(results),
                result={"status": "success", "data": results[-1], "items": results},
            )

        _set_content_task(
            task_id,
            status="completed",
            progress=100,
            current_agent=None,
            current_task="Content generation complete",
            result={"status": "success", "data": results[-1] if results else None, "items": results},
        )
        _save_backend_generation_log(db, CONTENT_GEN_TASKS.get(task_id, task))
    except Exception as exc:
        logger.error(f"Content generation task {task_id} failed: {exc}", exc_info=True)
        _set_content_task(
            task_id,
            status="error",
            error=str(exc),
            current_agent=None,
            current_task="Content generation failed",
            result={"status": "error", "error": str(exc)},
        )
        _save_backend_generation_log(db, CONTENT_GEN_TASKS.get(task_id, task))
    finally:
        db.close()


def _start_generation_thread(task_id: str) -> None:
    thread = threading.Thread(target=_run_generation_task, args=(task_id,), daemon=True)
    thread.start()


@content_generation_router.post("/campaigns/{campaign_id}/generate-piece")
async def generate_piece_endpoint(
    campaign_id: str,
    request_data: Dict[str, Any],
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start one backend-owned copy + image generation task for a single content item."""
    campaign = _verify_campaign_access(campaign_id, current_user, db)
    item = _normalize_generation_item(request_data, 0)
    task_id = _create_generation_task(
        campaign_id=campaign_id,
        user_id=current_user.id,
        scope="piece",
        items=[item],
        week=item.get("week"),
        day=item.get("day"),
        author_personality_id=request_data.get("author_personality_id") or request_data.get("authorPersonalityId"),
        brand_personality_id=request_data.get("brand_personality_id") or request_data.get("brandPersonalityId"),
        platform_settings=request_data.get("platformSettings") or request_data.get("platform_settings") or {},
        image_settings=request_data.get("image_settings") or request_data.get("imageSettings") or getattr(campaign, "image_settings_json", None),
    )
    if isinstance(CONTENT_GEN_TASKS[task_id].get("image_settings"), str):
        try:
            CONTENT_GEN_TASKS[task_id]["image_settings"] = json.loads(CONTENT_GEN_TASKS[task_id]["image_settings"])
        except Exception:
            CONTENT_GEN_TASKS[task_id]["image_settings"] = None
    _start_generation_thread(task_id)
    return {"status": "pending", "task_id": task_id, "message": "Generate piece started."}


@content_generation_router.post("/campaigns/{campaign_id}/generate-batch")
async def generate_batch_endpoint(
    campaign_id: str,
    request_data: Dict[str, Any],
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start one backend-owned ordered generation task for a batch of content items."""
    campaign = _verify_campaign_access(campaign_id, current_user, db)
    raw_items = request_data.get("items") or []
    if not raw_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No items provided.")
    items = [_normalize_generation_item(item, idx) for idx, item in enumerate(raw_items)]
    task_id = _create_generation_task(
        campaign_id=campaign_id,
        user_id=current_user.id,
        scope=request_data.get("scope") or "batch",
        items=items,
        author_personality_id=request_data.get("author_personality_id") or request_data.get("authorPersonalityId"),
        brand_personality_id=request_data.get("brand_personality_id") or request_data.get("brandPersonalityId"),
        platform_settings=request_data.get("platformSettings") or request_data.get("platform_settings") or {},
        image_settings=request_data.get("image_settings") or request_data.get("imageSettings") or getattr(campaign, "image_settings_json", None),
    )
    if isinstance(CONTENT_GEN_TASKS[task_id].get("image_settings"), str):
        try:
            CONTENT_GEN_TASKS[task_id]["image_settings"] = json.loads(CONTENT_GEN_TASKS[task_id]["image_settings"])
        except Exception:
            CONTENT_GEN_TASKS[task_id]["image_settings"] = None
    _start_generation_thread(task_id)
    return {"status": "pending", "task_id": task_id, "message": "Generate batch started."}


@content_generation_router.post("/campaigns/{campaign_id}/generate-day")
async def generate_day_endpoint(
    campaign_id: str,
    request_data: Dict[str, Any],
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start one backend-owned day task: cornerstone copy/image, then secondary copy/images."""
    campaign = _verify_campaign_access(campaign_id, current_user, db)
    raw_items = request_data.get("items") or []
    if not raw_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No items provided.")
    week = int(request_data.get("week") or 1)
    day = request_data.get("day") or "Monday"
    items = []
    for idx, raw in enumerate(raw_items):
        normalized = _normalize_generation_item({**raw, "week": raw.get("week", week), "day": raw.get("day", day)}, idx)
        items.append(normalized)
    task_id = _create_generation_task(
        campaign_id=campaign_id,
        user_id=current_user.id,
        scope="day",
        items=items,
        week=week,
        day=day,
        author_personality_id=request_data.get("author_personality_id") or request_data.get("authorPersonalityId"),
        brand_personality_id=request_data.get("brand_personality_id") or request_data.get("brandPersonalityId"),
        platform_settings=request_data.get("platformSettings") or request_data.get("platform_settings") or {},
        image_settings=request_data.get("image_settings") or request_data.get("imageSettings") or getattr(campaign, "image_settings_json", None),
    )
    if isinstance(CONTENT_GEN_TASKS[task_id].get("image_settings"), str):
        try:
            CONTENT_GEN_TASKS[task_id]["image_settings"] = json.loads(CONTENT_GEN_TASKS[task_id]["image_settings"])
        except Exception:
            CONTENT_GEN_TASKS[task_id]["image_settings"] = None
    _start_generation_thread(task_id)
    return {"status": "pending", "task_id": task_id, "message": "Generate day started."}


@content_generation_router.get("/campaigns/{campaign_id}/generate-content/status/{task_id}")
def get_content_generation_status_endpoint(
    campaign_id: str,
    task_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return backend task state for content generation polling."""
    _verify_campaign_access(campaign_id, current_user, db)
    task = CONTENT_GEN_TASKS.get(task_id)
    if not task or task.get("campaign_id") != campaign_id:
        return {
            "status": "pending",
            "progress": 0,
            "current_task": "Waiting for task",
            "current_agent": None,
            "agent_statuses": [],
            "items_done": 0,
            "items_total": 0,
            "result": None,
        }

    if task.get("status") in {"pending", "in_progress"}:
        try:
            started = datetime.fromisoformat(task.get("started_at"))
            if (datetime.utcnow() - started).total_seconds() > MAX_CONTENT_GEN_DURATION_SEC:
                _set_content_task(
                    task_id,
                    status="error",
                    error=f"Task exceeded maximum duration ({MAX_CONTENT_GEN_DURATION_SEC // 60} min)",
                    current_task="Content generation timed out",
                )
                task = CONTENT_GEN_TASKS.get(task_id, task)
        except Exception:
            pass

    return {
        "status": task.get("status", "pending"),
        "progress": task.get("progress", 0),
        "current_agent": task.get("current_agent"),
        "current_task": task.get("current_task"),
        "agent_statuses": task.get("agent_statuses", []),
        "error": task.get("error"),
        "result": task.get("result"),
        "items_done": task.get("items_done", 0),
        "items_total": task.get("items_total", 0),
        "scope": task.get("scope"),
        "week": task.get("week"),
        "day": task.get("day"),
        "steps": task.get("steps", []),
    }


@content_generation_router.get("/campaigns/{campaign_id}/generate-content/running-tasks")
def get_running_content_generation_tasks_endpoint(
    campaign_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List non-terminal content generation tasks for restoring the task panel after navigation."""
    _verify_campaign_access(campaign_id, current_user, db)
    task_ids = CONTENT_GEN_TASK_INDEX.get(campaign_id) or []
    if not isinstance(task_ids, list):
        task_ids = [task_ids]
    tasks = []
    for task_id in task_ids:
        task = CONTENT_GEN_TASKS.get(task_id)
        if not task or task.get("campaign_id") != campaign_id:
            continue
        if task.get("status") in {"completed", "error"}:
            continue
        tasks.append({
            "task_id": task_id,
            "scope": task.get("scope"),
            "week": task.get("week"),
            "day": task.get("day"),
            "progress": task.get("progress", 0),
            "status": task.get("status", "pending"),
            "items_done": task.get("items_done", 0),
            "items_total": task.get("items_total", 0),
            "current_task": task.get("current_task"),
            "steps": task.get("steps", []),
        })
    return {"status": "success", "tasks": tasks}


@content_generation_router.post("/analyze/test")
def test_analyze_endpoint():
    """Simple test endpoint to verify /analyze route is working"""
    return {"status": "ok", "message": "Test endpoint is reachable"}

@content_generation_router.post("/analyze")
def analyze_campaign(analyze_data: AnalyzeRequest, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Analyze campaign - Stub endpoint (returns task_id for now)
    TODO: Implement full analysis workflow
    
    IMPORTANT: This endpoint should NOT delete campaigns. It only starts analysis.
    REQUIRES AUTHENTICATION
    """
    try:
        logger.info(f"🔍 /analyze endpoint called - starting request processing")
        logger.info(f"🔍 SUCCESS: Request reached endpoint - Pydantic validation passed")
        logger.info(f"🔍 analyze_data type: {type(analyze_data)}")
        logger.info(f"🔍 analyze_data received: campaign_id={getattr(analyze_data, 'campaign_id', 'N/A')}, type={getattr(analyze_data, 'type', 'N/A')}")
        logger.info(f"🔍 current_user: {current_user}, user_id: {getattr(current_user, 'id', 'N/A')}")
        logger.info(f"🔍 db session: {db}")
        
        # Log all fields for debugging
        try:
            if hasattr(analyze_data, 'model_dump'):
                all_fields = analyze_data.model_dump()
            elif hasattr(analyze_data, 'dict'):
                all_fields = analyze_data.dict()
            else:
                all_fields = {k: getattr(analyze_data, k, None) for k in dir(analyze_data) if not k.startswith('_')}
            logger.info(f"🔍 All analyze_data fields: {json.dumps({k: str(v)[:100] for k, v in all_fields.items()}, indent=2)}")
        except Exception as log_err:
            logger.warning(f"⚠️ Could not log all fields: {log_err}")
        user_id = current_user.id
        campaign_id = analyze_data.campaign_id or f"campaign-{uuid.uuid4()}"
        campaign_name = analyze_data.campaign_name or "Unknown Campaign"
        logger.info(f"🔍 User ID: {user_id}, Campaign ID: {campaign_id}, Campaign Name: {campaign_name}")
        
        # If campaign_id is provided, verify ownership (or allow admin)
        if analyze_data.campaign_id:
            from models import Campaign
            is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
            if is_admin:
                # Admin can build any campaign
                campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
                if campaign:
                    logger.info(f"Admin user {current_user.id} building campaign {campaign_id} (owner: {campaign.user_id})")
            else:
                # Regular users can only build their own campaigns
                campaign = db.query(Campaign).filter(
                    Campaign.campaign_id == campaign_id,
                    Campaign.user_id == current_user.id
                ).first()
            
            if not campaign:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Campaign not found or access denied"
                )
        
        logger.info(f"🔍 /analyze POST endpoint called for campaign: {campaign_name} (ID: {campaign_id}) by user {user_id}")
        logger.info(f"🔍 Request data: campaign_name={analyze_data.campaign_name}, type={analyze_data.type}, keywords={len(analyze_data.keywords or [])} keywords")
        logger.info(f"🔍 CRITICAL: Keywords received from frontend: {analyze_data.keywords}")
        if analyze_data.keywords:
            logger.info(f"🔍 First keyword: '{analyze_data.keywords[0]}'")
        
        # Log Site Builder specific fields
        if analyze_data.type == "site_builder":
            logger.info(f"🏗️ Site Builder: site_base_url={analyze_data.site_base_url}")
            logger.info(f"🏗️ Site Builder: target_keywords={analyze_data.target_keywords}")
            logger.info(f"🏗️ Site Builder: top_ideas_count={analyze_data.top_ideas_count}")
        
        # CRITICAL: Validate Site Builder requirements BEFORE creating task
        # This prevents campaigns from showing progress when they should fail immediately
        if analyze_data.type == "site_builder":
            from models import Campaign
            import json
            campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
            
            # Get site_base_url - check request first, then database
            site_url = analyze_data.site_base_url
            if not site_url and campaign:
                site_url = campaign.site_base_url
            
            # Update campaign with site_base_url if provided in request but missing in DB
            if site_url and campaign and not campaign.site_base_url:
                campaign.site_base_url = site_url
                db.commit()
                logger.info(f"✅ Saved site_base_url to database during validation: {site_url}")
            
            # Update other Site Builder fields if provided
            if campaign:
                updated = False
                try:
                    if analyze_data.target_keywords:
                        # Ensure target_keywords is a list/array that can be serialized
                        if isinstance(analyze_data.target_keywords, list):
                            campaign.target_keywords_json = json.dumps(analyze_data.target_keywords)
                        else:
                            campaign.target_keywords_json = json.dumps([analyze_data.target_keywords])
                        updated = True
                    if analyze_data.top_ideas_count:
                        campaign.top_ideas_count = analyze_data.top_ideas_count
                        updated = True
                    if updated:
                        db.commit()
                        logger.info(f"✅ Campaign {campaign_id} updated with Site Builder fields")
                except Exception as update_error:
                    logger.error(f"❌ Error updating Site Builder fields: {update_error}")
                    # Don't fail the request, just log the error
                    db.rollback()
            
            # FAIL IMMEDIATELY if site_base_url is missing - don't create task
            if not site_url or not site_url.strip():
                logger.error(f"❌ Site Builder campaign requires site_base_url - FAILING BEFORE TASK CREATION")
                logger.error(f"❌ Request data.site_base_url: {analyze_data.site_base_url}")
                logger.error(f"❌ Campaign {campaign_id} has site_base_url=NULL in database")
                
                # Create error row so user can see what went wrong
                try:
                    from models import CampaignRawData
                    # datetime is already imported at top of file
                    error_row = CampaignRawData(
                        campaign_id=campaign_id,
                        source_url=f"error:missing_site_base_url",
                        fetched_at=datetime.utcnow(),
                        raw_html=None,
                        extracted_text=f"Site Builder: Campaign is missing site_base_url.\n\nThis campaign was created without a site URL. Please:\n1. Edit the campaign and set the Site Base URL\n2. Click 'Build Campaign' again\n\nCurrent campaign data:\n- Type: {analyze_data.type}\n- Request site_base_url: {analyze_data.site_base_url}\n- Request URLs: {analyze_data.urls if hasattr(analyze_data, 'urls') else 'N/A'}",
                        meta_json=json.dumps({"type": "error", "reason": "missing_site_base_url", "campaign_type": analyze_data.type})
                    )
                    db.add(error_row)
                    if campaign:
                        campaign.status = "INCOMPLETE"
                    db.commit()
                    logger.error(f"❌ Created error row for campaign {campaign_id} - missing site_base_url")
                except Exception as error_row_error:
                    logger.error(f"❌ Failed to create error row: {error_row_error}")
                    # Don't fail the request, just log the error
                    db.rollback()
                
                # Return error response - don't create task
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Site URL is required for Site Builder campaigns. Please edit the campaign and set the Site Base URL."
                )
        
        # Verify campaign exists and update Site Builder fields if provided (for non-Site Builder campaigns)
        try:
            from models import Campaign
            campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
            if campaign:
                logger.info(f"✅ Campaign {campaign_id} found in database (user_id: {campaign.user_id}, site_base_url: {campaign.site_base_url})")
            else:
                logger.warning(f"⚠️ Campaign {campaign_id} not found in database - analysis will continue anyway")
        except Exception as db_err:
            logger.warning(f"⚠️ Skipping campaign existence check: {db_err}")
        
        # Create task and seed progress (in-memory)
        # Only create task if validation passed (for Site Builder, this means site_base_url exists)
        try:
            task_id = str(uuid.uuid4())
            logger.info(f"🔍 Generated task_id: {task_id}")
            
            CONTENT_GEN_TASKS[task_id] = {
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "started_at": datetime.utcnow().isoformat(),
                "progress": 5,  # start at 5%
                "current_step": "initializing",
                "progress_message": "Starting analysis",
            }
            logger.info(f"🔍 Created CONTENT_GEN_TASKS entry for task_id: {task_id}")
            # Use list like brand_personalities so multiple tasks per campaign (analyze + generate-content + generate-day) coexist
            if campaign_id not in CONTENT_GEN_TASK_INDEX:
                CONTENT_GEN_TASK_INDEX[campaign_id] = []
            existing = CONTENT_GEN_TASK_INDEX[campaign_id]
            if not isinstance(existing, list):
                CONTENT_GEN_TASK_INDEX[campaign_id] = [existing] if existing else []
            CONTENT_GEN_TASK_INDEX[campaign_id].append(task_id)
            logger.info(f"🔍 Created CONTENT_GEN_TASK_INDEX entry: {campaign_id} -> appended {task_id}")
            
            logger.info(f"✅ Analysis task created (stub): task_id={task_id}, campaign_id={campaign_id}, user_id={user_id}")
        except Exception as task_creation_error:
            logger.error(f"❌ CRITICAL: Failed to create task: {task_creation_error}")
            import traceback
            logger.error(f"❌ Task creation traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create analysis task: {str(task_creation_error)}"
            )
        
        # Kick off a lightweight background job to simulate real steps and persist raw data
        def run_analysis_background(tid: str, cid: str, data: Dict[str, Any]):
            from database import SessionLocal
            from models import CampaignRawData, Campaign
            from pydantic import ValidationError
            session = SessionLocal()
            try:
                logger.info(f"🔵 Background thread started for task {tid}, campaign {cid}")
                
                # Reconstruct AnalyzeRequest from dict
                try:
                    analyze_data = AnalyzeRequest(**data)
                    logger.info(f"✅ Reconstructed AnalyzeRequest from dict")
                except (ValidationError, TypeError) as ve:
                    logger.error(f"❌ Failed to reconstruct AnalyzeRequest from dict: {ve}")
                    # Create a minimal AnalyzeRequest with just the essential fields
                    analyze_data = AnalyzeRequest(
                        campaign_id=data.get('campaign_id'),
                        campaign_name=data.get('campaign_name'),
                        type=data.get('type', 'keyword'),
                        site_base_url=data.get('site_base_url'),
                        target_keywords=data.get('target_keywords'),
                        top_ideas_count=data.get('top_ideas_count', 10),
                        most_recent_urls=data.get('most_recent_urls'),
                        keywords=data.get('keywords', []),
                        urls=data.get('urls', []),
                        description=data.get('description'),
                        query=data.get('query'),
                    )
                    logger.info(f"✅ Created minimal AnalyzeRequest from dict")
                
                # Use analyze_data instead of data from now on
                data = analyze_data
                
                # Helper to update task atomically
                def set_task(step: str, prog: int, msg: str):
                    task = CONTENT_GEN_TASKS.get(tid)
                    if not task:
                        logger.warning(f"⚠️ Task {tid} not found in CONTENT_GEN_TASKS dict")
                        return
                    task["current_step"] = step
                    task["progress"] = prog
                    task["progress_message"] = msg
                    logger.info(f"📊 Task {tid}: {prog}% - {step} - {msg}")

                # CRITICAL: Check if raw_data already exists for this campaign
                # If it does, skip scraping to prevent re-scraping and data growth
                # Raw data should only be written during initial scrape
                existing_raw_data = session.query(CampaignRawData).filter(
                    CampaignRawData.campaign_id == cid,
                    ~CampaignRawData.source_url.startswith("error:"),
                    ~CampaignRawData.source_url.startswith("placeholder:")
                ).first()
                
                if existing_raw_data:
                    logger.info(f"📋 Raw data already exists for campaign {cid} - skipping scrape phase to prevent data growth")
                    logger.info(f"📋 Raw data was created at: {existing_raw_data.fetched_at}")
                    set_task("raw_data_exists", 50, "Raw data already exists - using existing data")
                    set_task("complete", 100, "Analysis complete - using existing raw data")
                    camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                    if camp:
                        camp.status = "READY_TO_ACTIVATE"
                        camp.updated_at = datetime.utcnow()
                        session.commit()
                    logger.info(f"✅ Skipped scraping for campaign {cid} - raw data already exists")
                    return  # Exit early - don't write any new raw_data

                # CRITICAL: Set campaign status to PROCESSING at the start of analysis
                try:
                    camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                    if camp:
                        if camp.status != "PROCESSING":
                            camp.status = "PROCESSING"
                            camp.updated_at = datetime.utcnow()
                            session.commit()
                            logger.info(f"✅ Set campaign {cid} status to PROCESSING at analysis start")
                        else:
                            logger.info(f"ℹ️ Campaign {cid} already has PROCESSING status")
                    else:
                        logger.warning(f"⚠️ Campaign {cid} not found when trying to set PROCESSING status")
                except Exception as status_err:
                    logger.error(f"❌ Failed to set PROCESSING status for campaign {cid}: {status_err}")
                    # Don't fail the analysis, just log the error
                
                # Step 1: collecting inputs
                logger.info(f"📝 Step 1: Collecting inputs for campaign {cid}")
                set_task("collecting_inputs", 15, "Collecting inputs and settings")
                
                # Validate Site Builder requirements EARLY (fail at "Initializing" stage)
                # Use short timeouts (5s) so we don't hang forever on slow/unreachable sites
                SITE_VALIDATION_TIMEOUT = 5
                if data.type == "site_builder":
                    from models import Campaign
                    # json is already imported globally at top of file
                    
                    # Get site URL - check request data first, then database
                    # DO NOT fall back to urls array - site_base_url must be explicitly set
                    site_url = getattr(data, 'site_base_url', None)
                    camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                    
                    if not site_url:
                        # Try to get from campaign in database
                        if camp and camp.site_base_url:
                            site_url = camp.site_base_url
                            logger.info(f"✅ Retrieved site_base_url from campaign database: {site_url}")
                        # NOTE: We intentionally do NOT fall back to data.urls - site_base_url must be explicitly saved
                        # This ensures the field is properly persisted in the database
                    elif camp and not camp.site_base_url:
                        # If site_url is in request but not in database, save it now
                        camp.site_base_url = site_url
                        session.commit()
                        logger.info(f"✅ Saved site_base_url to database during validation: {site_url}")
                    
                    # FAIL EARLY if site_base_url is missing (no fallback to urls array)
                    if not site_url or not site_url.strip():
                        logger.error(f"❌ Site Builder campaign requires site_base_url - FAILING AT INITIALIZING STAGE")
                        logger.error(f"❌ Request data.site_base_url: {getattr(data, 'site_base_url', None)}")
                        logger.error(f"❌ Request data.urls: {data.urls if hasattr(data, 'urls') else 'N/A'}")
                        logger.error(f"❌ Campaign {cid} has site_base_url=NULL in database")
                        
                        # Create error row so user can see what went wrong
                        error_row = CampaignRawData(
                            campaign_id=cid,
                            source_url=f"error:missing_site_base_url",
                            fetched_at=datetime.utcnow(),
                            raw_html=None,
                            extracted_text=f"Site Builder: Campaign is missing site_base_url.\n\nThis campaign was created without a site URL. Please:\n1. Edit the campaign and set the Site Base URL\n2. Click 'Build Campaign' again\n\nCurrent campaign data:\n- Type: {data.type}\n- Request site_base_url: {getattr(data, 'site_base_url', None)}\n- Request URLs: {data.urls if hasattr(data, 'urls') else 'N/A'}",
                            meta_json=json.dumps({"type": "error", "reason": "missing_site_base_url", "campaign_type": data.type})
                        )
                        session.add(error_row)
                        session.commit()
                        logger.error(f"❌ Created error row for campaign {cid} - missing site_base_url")
                        
                        # Set campaign status to INCOMPLETE
                        camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                        if camp:
                            camp.status = "INCOMPLETE"
                            camp.updated_at = datetime.utcnow()
                            session.commit()
                            logger.error(f"❌ Campaign {cid} status set to INCOMPLETE due to missing site_base_url")
                        
                        # Set progress to error state - FAIL AT INITIALIZING STAGE
                        set_task("error", 15, "Site URL is required for Site Builder campaigns. Please edit the campaign and set the Site Base URL.")
                        logger.error(f"❌ Campaign {cid} analysis FAILED at Initializing stage - site_base_url is missing")
                        return
                    
                    # VALIDATE URL FORMAT AND ACCESSIBILITY AT INITIALIZATION
                    logger.info(f"🔍 Validating site URL format and accessibility: {site_url}")
                    set_task("validating_url", 18, f"Validating site URL: {site_url}")
                    
                    try:
                        from sitemap_parser import validate_url_format, validate_url_accessibility, quick_sitemap_check
                    except ImportError as import_error:
                        logger.error(f"❌ Failed to import validation functions: {import_error}")
                        logger.error(f"❌ This is a critical error - validation cannot proceed")
                        # Don't fail the campaign, just log and continue without validation
                        logger.warning(f"⚠️ Continuing without URL validation - this should not happen")
                        # Skip validation and proceed to sitemap parsing
                        pass
                    else:
                        # Step 1: Validate URL format
                        try:
                            is_valid_format, format_error = validate_url_format(site_url)
                        except Exception as format_validation_error:
                            logger.error(f"❌ Error during URL format validation: {format_validation_error}")
                            import traceback
                            logger.error(traceback.format_exc())
                            # Don't fail - just log and continue
                            is_valid_format, format_error = True, None
                        
                        if not is_valid_format:
                            error_msg = f"Invalid URL format: {format_error}"
                            logger.error(f"❌ {error_msg}")
                            
                            error_row = CampaignRawData(
                                campaign_id=cid,
                                source_url=f"error:invalid_url_format",
                                fetched_at=datetime.utcnow(),
                                raw_html=None,
                                extracted_text=f"Site Builder: Invalid URL format.\n\nError: {format_error}\n\nURL provided: {site_url}\n\nPlease edit the campaign and provide a valid URL starting with http:// or https://",
                                meta_json=json.dumps({"type": "error", "reason": "invalid_url_format", "site_url": site_url, "error": format_error})
                            )
                            session.add(error_row)
                            if camp:
                                camp.status = "INCOMPLETE"
                                camp.updated_at = datetime.utcnow()
                            session.commit()
                            set_task("error", 18, error_msg)
                            logger.error(f"❌ Campaign {cid} analysis FAILED at Initializing stage - invalid URL format")
                            return
                    
                        # Step 2: Validate URL accessibility (DNS, connectivity, HTTP status)
                        logger.info(f"🔍 Checking if site is accessible: {site_url}")
                        try:
                            is_accessible, access_error, http_status = validate_url_accessibility(site_url, timeout=SITE_VALIDATION_TIMEOUT)
                        except Exception as access_validation_error:
                            logger.error(f"❌ Error during URL accessibility validation: {access_validation_error}")
                            import traceback
                            logger.error(traceback.format_exc())
                            # Don't fail - just log and continue (validation is best effort)
                            is_accessible, access_error, http_status = True, None, None
                        
                        if not is_accessible:
                            error_msg = f"Site is not accessible: {access_error}"
                            logger.error(f"❌ {error_msg}")
                            
                            error_row = CampaignRawData(
                                campaign_id=cid,
                                source_url=f"error:site_not_accessible",
                                fetched_at=datetime.utcnow(),
                                raw_html=None,
                                extracted_text=f"Site Builder: Site is not accessible.\n\nError: {access_error}\n\nURL: {site_url}\nHTTP Status: {http_status if http_status else 'N/A (connection failed)'}\n\nPossible reasons:\n- Domain does not exist (DNS error)\n- Server is down or not responding\n- Site requires authentication\n- Network connectivity issues\n\nPlease verify the URL is correct and the site is accessible.",
                                meta_json=json.dumps({"type": "error", "reason": "site_not_accessible", "site_url": site_url, "error": access_error, "http_status": http_status})
                            )
                            session.add(error_row)
                            if camp:
                                camp.status = "INCOMPLETE"
                                camp.updated_at = datetime.utcnow()
                            session.commit()
                            set_task("error", 18, error_msg)
                            logger.error(f"❌ Campaign {cid} analysis FAILED at Initializing stage - site not accessible")
                            return
                    
                        logger.info(f"✅ Site URL is accessible: {site_url} (HTTP {http_status})")
                        
                        # Step 3: Quick sitemap check (fail early if sitemap definitely doesn't exist)
                        logger.info(f"🔍 Performing quick sitemap check: {site_url}")
                        set_task("checking_sitemap", 20, f"Checking for sitemap at {site_url}")
                        try:
                            sitemap_found, sitemap_url, sitemap_error = quick_sitemap_check(site_url, timeout=SITE_VALIDATION_TIMEOUT)
                        except Exception as sitemap_check_error:
                            logger.error(f"❌ Error during quick sitemap check: {sitemap_check_error}")
                            import traceback
                            logger.error(traceback.format_exc())
                            # Don't fail - just log and continue (will try full parsing)
                            sitemap_found, sitemap_url, sitemap_error = False, None, None
                    
                        if not sitemap_found:
                            # If quick check fails, we'll still try full parsing, but log a warning
                            # Only fail if the error indicates the site itself is inaccessible
                            if sitemap_error and ("not accessible" in sitemap_error.lower() or "dns" in sitemap_error.lower() or "connection" in sitemap_error.lower()):
                                error_msg = f"Sitemap check failed: {sitemap_error}"
                                logger.error(f"❌ {error_msg}")
                                
                                error_row = CampaignRawData(
                                    campaign_id=cid,
                                    source_url=f"error:sitemap_check_failed",
                                    fetched_at=datetime.utcnow(),
                                    raw_html=None,
                                    extracted_text=f"Site Builder: Sitemap check failed during initialization.\n\nError: {sitemap_error}\n\nURL: {site_url}\n\nThis usually means:\n- The site is not accessible\n- DNS resolution failed\n- Network connectivity issues\n\nPlease verify the site is accessible and try again.",
                                    meta_json=json.dumps({"type": "error", "reason": "sitemap_check_failed", "site_url": site_url, "error": sitemap_error})
                                )
                                session.add(error_row)
                                if camp:
                                    camp.status = "INCOMPLETE"
                                    camp.updated_at = datetime.utcnow()
                                session.commit()
                                set_task("error", 20, error_msg)
                                logger.error(f"❌ Campaign {cid} analysis FAILED at Initializing stage - sitemap check failed")
                                return
                            else:
                                # Sitemap not found at common locations, but site is accessible
                                # We'll proceed to full parsing which will try more locations
                                logger.warning(f"⚠️ Sitemap not found at common locations, but site is accessible. Will attempt full discovery.")
                        else:
                            logger.info(f"✅ Sitemap found at: {sitemap_url}")
                
                time.sleep(1)  # Brief pause before proceeding

                # Step 2: Web scraping with DuckDuckGo + Playwright (or Site Builder sitemap parsing)
                logger.info(f"📝 Step 2: Starting content collection for campaign {cid} (type: {data.type})")
                set_task("fetching_content", 25, "Collecting content from site" if data.type == "site_builder" else "Searching web and scraping content")
                
                # Handle Site Builder campaign type
                if data.type == "site_builder":
                    from sitemap_parser import parse_sitemap_from_site
                    from gap_analysis import identify_content_gaps, rank_gaps_by_priority
                    from text_processing import extract_topics
                    import json
                    
                    # Get site URL and target keywords (we already validated it exists above)
                    # Use the site_url we validated in Step 1 - no need to check again
                    # If we got here, site_url was already validated and set
                    site_url = getattr(data, 'site_base_url', None)
                    if not site_url:
                        # Try to get from campaign in database (should already be there from validation)
                        camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                        if camp and camp.site_base_url:
                            site_url = camp.site_base_url
                            logger.info(f"✅ Retrieved site_base_url from campaign database: {site_url}")
                        else:
                            # This should never happen if validation worked, but log error if it does
                            logger.error(f"❌ site_url is missing after validation - this should not happen")
                            logger.error(f"❌ Request data.site_base_url: {getattr(data, 'site_base_url', None)}")
                            logger.error(f"❌ Campaign {cid} site_base_url in database: {camp.site_base_url if camp else 'campaign not found'}")
                    
                    target_keywords = getattr(data, 'target_keywords', None) or data.keywords or []
                    top_ideas_count = getattr(data, 'top_ideas_count', 10)
                    
                    logger.info(f"🏗️ Site Builder: site_url={site_url}, target_keywords={target_keywords}, top_ideas_count={top_ideas_count}")
                    
                    # This check should never trigger now since we validate above, but keep as safety
                    if not site_url:
                        logger.error(f"❌ Site Builder campaign requires site_base_url")
                        logger.error(f"❌ Request data.site_base_url: {getattr(data, 'site_base_url', None)}")
                        logger.error(f"❌ Request data.urls: {data.urls if hasattr(data, 'urls') else 'N/A'}")
                        logger.error(f"❌ Campaign {cid} has site_base_url=NULL in database")
                        
                        # Create error row so user can see what went wrong
                        error_row = CampaignRawData(
                            campaign_id=cid,
                            source_url=f"error:missing_site_base_url",
                            fetched_at=datetime.utcnow(),
                            raw_html=None,
                            extracted_text=f"Site Builder: Campaign is missing site_base_url.\n\nThis campaign was created without a site URL. Please:\n1. Edit the campaign and set the Site Base URL\n2. Click 'Build Campaign' again\n\nCurrent campaign data:\n- Type: {data.type}\n- Request site_base_url: {getattr(data, 'site_base_url', None)}\n- Request URLs: {data.urls if hasattr(data, 'urls') else 'N/A'}",
                            meta_json=json.dumps({"type": "error", "reason": "missing_site_base_url", "campaign_type": data.type})
                        )
                        session.add(error_row)
                        session.commit()
                        logger.error(f"❌ Created error row for campaign {cid} - missing site_base_url")
                        
                        # Set campaign status to INCOMPLETE
                        camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                        if camp:
                            camp.status = "INCOMPLETE"
                            camp.updated_at = datetime.utcnow()
                            session.commit()
                            logger.error(f"❌ Campaign {cid} status set to INCOMPLETE due to missing site_base_url")
                        
                        # Set progress to error state
                        set_task("error", 95, "Site URL is required for Site Builder campaigns. Please edit the campaign and set the Site Base URL.")
                        logger.error(f"❌ Campaign {cid} analysis failed - site_base_url is missing")
                        return
                    
                    logger.info(f"🏗️ Site Builder: Parsing sitemap from {site_url}")
                    logger.info(f"🏗️ Site Builder: Site URL details - scheme: {urlparse(site_url).scheme}, netloc: {urlparse(site_url).netloc}")
                    set_task("parsing_sitemap", 30, f"Parsing sitemap from {site_url}")
                    
                    # Parse sitemap to get all URLs
                    logger.info(f"🏗️ Site Builder: Starting sitemap parsing for {site_url}")
                    # For Site Builder, ignore max_pages from extraction settings
                    # Use a high limit to get all URLs, then filter by most_recent_urls if provided
                    max_sitemap_urls = 10000  # High limit to get all URLs from sitemap
                    # Get most_recent_urls setting if provided
                    most_recent_urls = getattr(data, 'most_recent_urls', None)
                    logger.info(f"🔍 DEBUG: most_recent_urls value received: {most_recent_urls} (type: {type(most_recent_urls)})")
                    logger.info(f"🔍 DEBUG: data object has most_recent_urls attr: {hasattr(data, 'most_recent_urls')}")
                    if hasattr(data, 'most_recent_urls'):
                        logger.info(f"🔍 DEBUG: data.most_recent_urls = {getattr(data, 'most_recent_urls', 'NOT_FOUND')}")
                    if most_recent_urls:
                        logger.info(f"📅 Site Builder: Will filter to {most_recent_urls} most recent URLs by date")
                    else:
                        logger.warning(f"⚠️ Site Builder: most_recent_urls is None/0/empty - Will collect ALL URLs from sitemap (no date filter)")
                        logger.warning(f"⚠️ This means it will scrape all {len(sitemap_urls) if 'sitemap_urls' in locals() else 'unknown'} URLs instead of limiting to most recent")
                    
                    # Parse sitemap (we already validated accessibility at initialization, so this should work)
                    # But handle network failures gracefully with better error messages
                    try:
                        sitemap_urls = parse_sitemap_from_site(site_url, max_urls=max_sitemap_urls, most_recent=most_recent_urls)
                        logger.info(f"✅ Sitemap parsing complete: Found {len(sitemap_urls)} URLs from sitemap")
                        if len(sitemap_urls) > 0:
                            logger.info(f"✅ First 5 sitemap URLs: {sitemap_urls[:5]}")
                    except Exception as sitemap_error:
                        # Handle different types of errors with appropriate messages
                        error_str = str(sitemap_error).lower()
                        sitemap_urls = []
                        
                        # Check for timeout errors
                        if "timeout" in error_str or "timed out" in error_str:
                            logger.error(f"❌ Sitemap parsing timed out: {sitemap_error}")
                            error_row = CampaignRawData(
                                campaign_id=cid,
                                source_url=f"error:sitemap_timeout",
                                fetched_at=datetime.utcnow(),
                                raw_html=None,
                                extracted_text=f"Site Builder: Sitemap parsing timed out.\n\nURL: {site_url}\n\nThis usually means:\n- The server is slow to respond\n- Network connectivity issues\n- The sitemap is very large\n\nPlease try again or check your network connection.",
                                meta_json=json.dumps({"type": "error", "reason": "sitemap_timeout", "site_url": site_url})
                            )
                            session.add(error_row)
                            if camp:
                                camp.status = "INCOMPLETE"
                                camp.updated_at = datetime.utcnow()
                            session.commit()
                            set_task("error", 30, f"Sitemap parsing timed out for {site_url}")
                            logger.error(f"❌ Campaign {cid} analysis FAILED - sitemap parsing timed out")
                            return
                        # Check for connection errors
                        elif "connection" in error_str or "dns" in error_str or "refused" in error_str:
                            logger.error(f"❌ Sitemap parsing connection error: {sitemap_error}")
                            if "dns" in error_str or "name resolution" in error_str:
                                error_msg = "DNS resolution failed during sitemap parsing"
                            elif "refused" in error_str:
                                error_msg = "Connection refused during sitemap parsing"
                            else:
                                error_msg = f"Connection error: {str(sitemap_error)}"
                            
                            error_row = CampaignRawData(
                                campaign_id=cid,
                                source_url=f"error:sitemap_connection_error",
                                fetched_at=datetime.utcnow(),
                                raw_html=None,
                                extracted_text=f"Site Builder: Connection error during sitemap parsing.\n\nError: {error_msg}\n\nURL: {site_url}\n\nThis usually means:\n- Network connectivity issues\n- DNS resolution problems\n- Server is not accepting connections\n\nPlease check your network connection and try again.",
                                meta_json=json.dumps({"type": "error", "reason": "sitemap_connection_error", "site_url": site_url, "error": error_msg})
                            )
                            session.add(error_row)
                            if camp:
                                camp.status = "INCOMPLETE"
                                camp.updated_at = datetime.utcnow()
                            session.commit()
                            set_task("error", 30, error_msg)
                            logger.error(f"❌ Campaign {cid} analysis FAILED - sitemap connection error")
                            return
                        # Handle all other exceptions
                        else:
                            logger.error(f"❌ Exception during sitemap parsing: {sitemap_error}")
                            import traceback
                            logger.error(traceback.format_exc())
                            
                            error_row = CampaignRawData(
                                campaign_id=cid,
                                source_url=f"error:sitemap_parsing_exception",
                                fetched_at=datetime.utcnow(),
                                raw_html=None,
                                extracted_text=f"Site Builder: Unexpected error during sitemap parsing.\n\nError: {str(sitemap_error)}\n\nURL: {site_url}\n\nPlease check the backend logs for more details.",
                                meta_json=json.dumps({"type": "error", "reason": "sitemap_parsing_exception", "site_url": site_url, "error": str(sitemap_error)})
                            )
                            session.add(error_row)
                            if camp:
                                camp.status = "INCOMPLETE"
                                camp.updated_at = datetime.utcnow()
                            session.commit()
                            set_task("error", 30, f"Sitemap parsing failed: {str(sitemap_error)}")
                            logger.error(f"❌ Campaign {cid} analysis FAILED - sitemap parsing exception")
                            return
                    
                    if not sitemap_urls:
                        logger.error(f"❌ Site Builder: No URLs found in sitemap for {site_url}")
                        logger.error(f"❌ This could mean:")
                        logger.error(f"   1. sitemap.xml doesn't exist at common locations ({site_url}/sitemap.xml)")
                        logger.error(f"   2. sitemap is empty or malformed")
                        logger.error(f"   3. sitemap requires authentication")
                        logger.error(f"   4. sitemap is blocked by robots.txt or CDN")
                        logger.error(f"   5. Network/timeout issues accessing the sitemap")
                        
                        # Create error row so user can see what went wrong
                        error_row = CampaignRawData(
                            campaign_id=cid,
                            source_url=f"error:sitemap_parsing_failed",
                            fetched_at=datetime.utcnow(),
                            raw_html=None,
                            extracted_text=f"Site Builder: Failed to parse sitemap from {site_url}. No URLs found.\n\nPossible reasons:\n- sitemap.xml doesn't exist at {site_url}/sitemap.xml\n- sitemap is empty or malformed\n- sitemap requires authentication\n- Network/timeout issues\n\nPlease verify the sitemap exists and is accessible. You can check by visiting {site_url}/sitemap.xml in your browser.",
                            meta_json=json.dumps({"type": "error", "reason": "sitemap_parsing_failed", "site_url": site_url})
                        )
                        session.add(error_row)
                        camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                        if camp:
                            camp.status = "INCOMPLETE"
                            camp.updated_at = datetime.utcnow()
                        session.commit()
                        logger.error(f"❌ Created error row for campaign {cid} - sitemap parsing failed")
                        
                        # Set progress to error state at LOW percentage (30%) - FAIL EARLY
                        set_task("error", 30, f"Sitemap parsing failed for {site_url}. No URLs found. Check if sitemap.xml exists.")
                        logger.error(f"❌ Campaign {cid} analysis FAILED at parsing stage - sitemap parsing returned no URLs")
                        return
                    
                    # Validate URLs before scraping
                    valid_urls = []
                    invalid_urls = []
                    for url in sitemap_urls:
                        try:
                            parsed = urlparse(url)
                            if parsed.scheme in ('http', 'https') and parsed.netloc:
                                valid_urls.append(url)
                            else:
                                invalid_urls.append(url)
                                logger.warning(f"⚠️ Invalid URL from sitemap: {url}")
                        except Exception as e:
                            invalid_urls.append(url)
                            logger.warning(f"⚠️ Error validating URL {url}: {e}")
                    
                    if invalid_urls:
                        logger.warning(f"⚠️ Found {len(invalid_urls)} invalid URLs out of {len(sitemap_urls)} total")
                    
                    if not valid_urls:
                        logger.error(f"❌ Site Builder: All {len(sitemap_urls)} URLs from sitemap are invalid!")
                        error_row = CampaignRawData(
                            campaign_id=cid,
                            source_url=f"error:invalid_sitemap_urls",
                            fetched_at=datetime.utcnow(),
                            raw_html=None,
                            extracted_text=f"Site Builder: Found {len(sitemap_urls)} URLs in sitemap, but all are invalid. Please check the sitemap format.",
                            meta_json=json.dumps({"type": "error", "reason": "invalid_sitemap_urls", "site_url": site_url, "url_count": len(sitemap_urls)})
                        )
                        session.add(error_row)
                        session.commit()
                        logger.error(f"❌ Created error row for campaign {cid} - all sitemap URLs invalid")
                        set_task("error", 0, f"All {len(sitemap_urls)} URLs from sitemap are invalid")
                        return
                    
                    logger.info(f"✅ Validated {len(valid_urls)} valid URLs out of {len(sitemap_urls)} total")
                    
                    # Use validated sitemap URLs for scraping
                    urls = valid_urls
                    keywords = []  # Don't use keywords for Site Builder
                    depth = 1  # Only scrape the URLs from sitemap
                    max_pages = len(valid_urls)  # Scrape all validated URLs from sitemap
                    include_images = False
                    include_links = False
                    
                    logger.info(f"🏗️ Site Builder: Ready to scrape {len(valid_urls)} URLs")
                    logger.info(f"🏗️ Site Builder: First 5 URLs: {valid_urls[:5]}")
                else:
                    # Standard campaign types (keyword, url, trending)
                    urls = data.urls or []
                    keywords = data.keywords or []
                    depth = data.depth if hasattr(data, 'depth') and data.depth else 1
                    max_pages = data.max_pages if hasattr(data, 'max_pages') and data.max_pages else 10
                    include_images = data.include_images if hasattr(data, 'include_images') else False
                    include_links = data.include_links if hasattr(data, 'include_links') else False
                
                logger.info(f"📝 Scraping settings: URLs={len(urls)}, Keywords={len(keywords)}, depth={depth}, max_pages={max_pages}")
                logger.info(f"📝 URL list: {urls[:10] if urls else []}")  # Show first 10 URLs
                logger.info(f"📝 Keywords list: {keywords}")
                # Only warn about missing keywords if we also don't have URLs (Site Builder uses URLs only)
                if not keywords and not urls:
                    logger.error(f"❌ CRITICAL: No keywords or URLs provided! This will cause scraping to fail.")
                elif not keywords and urls:
                    logger.info(f"ℹ️ No keywords provided, but {len(urls)} URLs will be scraped (Site Builder mode)")
                elif keywords and not urls:
                    logger.info(f"ℹ️ No URLs provided, will search DuckDuckGo for keywords: {keywords}")
                
                # Import web scraping module
                scrape_campaign_data = None
                try:
                    from web_scraping import scrape_campaign_data
                except ImportError as e:
                    logger.error(f"❌ Failed to import web_scraping module: {e}")
                    scrape_campaign_data = None  # Mark as unavailable
                
                # Perform actual web scraping
                created = 0
                now = datetime.utcnow()
                
                if scrape_campaign_data is None:
                    # Module import failed - create error row
                    logger.error(f"❌ Cannot proceed with scraping - module import failed")
                    row = CampaignRawData(
                        campaign_id=cid,
                        source_url="error:module_import_failed",
                        fetched_at=now,
                        raw_html=None,
                        extracted_text=f"Web scraping module not available. Please check server logs.",
                        meta_json=json.dumps({"type": "error", "reason": "module_import_failed"})
                    )
                    session.add(row)
                    created = 1
                elif not urls and not keywords:
                    logger.warning(f"⚠️ No URLs or keywords provided for campaign {cid}")
                    # Create error row (not placeholder) so user knows something went wrong
                    error_text = f"Site Builder: No URLs or keywords provided for scraping.\n\nCampaign type: {data.type}\nSite URL: {getattr(data, 'site_base_url', 'Not provided')}\nURLs: {len(data.urls or [])}\nKeywords: {len(data.keywords or [])}\n\nThis usually means sitemap parsing failed or returned no URLs."
                    row = CampaignRawData(
                        campaign_id=cid,
                        source_url="error:no_urls_or_keywords",
                        fetched_at=now,
                        raw_html=None,
                        extracted_text=error_text,
                        meta_json=json.dumps({"type": "error", "reason": "no_urls_or_keywords", "campaign_type": data.type, "site_base_url": getattr(data, 'site_base_url', None)})
                    )
                    session.add(row)
                    created = 1
                    logger.error(f"❌ Created error row for campaign {cid} - no URLs or keywords provided")
                else:
                    # Perform real web scraping
                    logger.info(f"🚀 Starting web scraping for campaign {cid}")
                    logger.info(f"📋 Parameters: keywords={keywords}, urls={urls}, depth={depth}, max_pages={max_pages}, include_images={include_images}, include_links={include_links}")
                    
                    try:
                        logger.info(f"🚀 Calling scrape_campaign_data with: keywords={keywords}, urls={urls}, query={data.query or ''}, depth={depth}, max_pages={max_pages}")
                        # Update progress to show scraping is starting
                        set_task("scraping", 50, f"Scraping 0/{len(urls)} URLs... (this may take several minutes)")
                        
                        # Progress callback to update as each URL is scraped
                        def update_scraping_progress(scraped: int, total: int, progress_pct: int):
                            set_task("scraping", progress_pct, f"Scraping {scraped}/{total} URLs... ({progress_pct}%)")
                        
                        scraped_results = scrape_campaign_data(
                            keywords=keywords,
                            urls=urls,
                            query=data.query or "",
                            depth=depth,
                            max_pages=max_pages,
                            include_images=include_images,
                            include_links=include_links,
                            progress_callback=update_scraping_progress
                        )
                        
                        logger.info(f"✅ Web scraping completed: {len(scraped_results)} pages scraped")
                        # Update progress after scraping completes
                        set_task("scraping_complete", 70, f"Scraped {len(scraped_results)} pages, saving to database...")
                        logger.info(f"📊 Progress updated: 70% - scraping_complete")
                        
                        # Log detailed results for diagnostics
                        if len(scraped_results) == 0:
                            logger.error(f"❌ CRITICAL: Scraping returned 0 results for campaign {cid}")
                            logger.error(f"❌ Campaign type: {data.type}")
                            logger.error(f"❌ Keywords used: {keywords}")
                            logger.error(f"❌ URLs provided: {len(urls) if urls else 0} URLs")
                            if urls:
                                logger.error(f"❌ First 5 URLs: {urls[:5]}")
                            logger.error(f"❌ Query: {data.query or '(empty)'}")
                            logger.error(f"❌ Depth: {depth}, Max pages: {max_pages}")
                            logger.error(f"❌ This likely means scraping failed - check Playwright/DuckDuckGo availability")
                            
                            # Create error row for ALL campaign types when scraping returns 0 results
                            if data.type == "site_builder":
                                error_text = f"Site Builder: Sitemap parsing succeeded ({len(urls)} URLs found), but scraping returned 0 results.\n\nPossible reasons:\n- Network/timeout issues accessing URLs\n- URLs require authentication\n- URLs are blocked by robots.txt\n- Playwright/scraping service unavailable\n\nPlease check backend logs for details."
                                error_reason = "scraping_failed"
                                error_meta = {"type": "error", "reason": "scraping_failed", "urls_count": len(urls), "urls": urls[:10]}
                            else:
                                # Keyword or other campaign types
                                error_text = f"No results from web scraping.\n\nCampaign type: {data.type}\nKeywords: {keywords}\nURLs: {len(urls) if urls else 0} URLs\nQuery: {data.query or '(empty)'}\n\nPossible reasons:\n- DuckDuckGo search returned no results\n- Playwright/scraping service unavailable\n- Network/firewall blocking\n- Invalid or empty keywords\n\nPlease check backend logs for details."
                                error_reason = "no_scrape_results"
                                error_meta = {"type": "error", "reason": "no_scrape_results", "keywords": keywords, "urls_count": len(urls) if urls else 0, "query": data.query or ""}
                            
                            error_row = CampaignRawData(
                                campaign_id=cid,
                                source_url=f"error:{error_reason}",
                                fetched_at=datetime.utcnow(),
                                raw_html=None,
                                extracted_text=error_text,
                                meta_json=json.dumps(error_meta)
                            )
                            session.add(error_row)
                            try:
                                session.commit()
                                created = 1  # Mark that we created an error row
                                logger.error(f"❌ Created error row for campaign {cid} - scraping returned 0 results")
                            except Exception as commit_err:
                                logger.error(f"❌ Failed to commit error row for campaign {cid}: {commit_err}")
                                session.rollback()
                                # Continue anyway - we'll check for created == 0 later
                        else:
                            logger.info(f"📊 Scraping results breakdown:")
                            success_count = 0
                            error_count = 0
                            total_text_length = 0
                            for i, result in enumerate(scraped_results):
                                url = result.get("url", "unknown")
                                text = result.get("text", "")
                                text_len = len(text)
                                has_error = result.get("error") is not None
                                if has_error:
                                    error_count += 1
                                    logger.warning(f"  [{i+1}] ❌ {url}: ERROR - {result.get('error')}")
                                else:
                                    success_count += 1
                                    total_text_length += text_len
                                    if i < 5:  # Log first 5 successful results
                                        logger.info(f"  [{i+1}] ✅ {url}: {text_len} chars")
                            logger.info(f"📊 Summary: {success_count} successful, {error_count} errors, {total_text_length} total chars")
                            
                            if success_count == 0:
                                logger.error(f"❌ CRITICAL: All {len(scraped_results)} scraping attempts failed!")
                        
                        # Store scraped data in database
                        # Initialize tracking variables before try block so they're accessible later
                        skipped_count = 0
                        created = 0
                        total_urls_scraped = len(scraped_results) if 'scraped_results' in locals() else 0
                        
                        try:
                            # Ensure json is available (it's imported globally, but ensure it's in scope)
                            import json as json_module
                            json = json_module  # Use global json module
                            
                            logger.info(f"💾 Starting to save {len(scraped_results)} scraped results to database...")
                            
                            # Update total_urls_scraped now that we're in the try block
                            total_urls_scraped = len(scraped_results)
                            
                            # CRITICAL: Check for existing scraped data to avoid duplicates
                            # Query all existing URLs for this campaign to reuse instead of re-scraping
                            existing_urls = {}
                            try:
                                existing_rows = session.query(CampaignRawData).filter(
                                    CampaignRawData.campaign_id == cid,
                                    ~CampaignRawData.source_url.startswith("error:"),
                                    ~CampaignRawData.source_url.startswith("placeholder:")
                                ).all()
                                for row in existing_rows:
                                    if row.source_url and row.extracted_text and len(row.extracted_text.strip()) > 10:
                                        existing_urls[row.source_url] = row
                                logger.info(f"📋 Found {len(existing_urls)} existing scraped URLs for campaign {cid} - will reuse instead of re-scraping")
                            except Exception as query_err:
                                logger.warning(f"⚠️ Error querying existing URLs: {query_err}, will proceed with saving all results")
                                existing_urls = {}
                            
                            skipped_count = 0
                            for i, result in enumerate(scraped_results, 1):
                                # Update progress periodically during database save (every 10 items)
                                if i % 10 == 0 or i == len(scraped_results):
                                    set_task("scraping_complete", 70, f"Saving to database... ({i}/{len(scraped_results)})")
                                    logger.debug(f"💾 Saving progress: {i}/{len(scraped_results)}")
                                url = result.get("url", "unknown")
                                text = result.get("text", "")
                                html = result.get("html")
                                images = result.get("images", [])
                                links = result.get("links", [])
                                error = result.get("error")
                                depth_level = result.get("depth", 0)
                                
                                # CRITICAL: Skip if URL already exists in database (reuse existing data)
                                if url in existing_urls and not error:
                                    skipped_count += 1
                                    existing_row = existing_urls[url]
                                    logger.debug(f"♻️ Skipping {url} - already exists in database (DB ID: {existing_row.id}, {len(existing_row.extracted_text or '')} chars)")
                                    continue  # Skip creating duplicate row
                                
                                # Build metadata JSON
                                meta = {
                                    "type": "scraped",
                                    "depth": depth_level,
                                    "scraped_at": result.get("scraped_at"),
                                    "has_images": len(images) > 0,
                                    "image_count": len(images),
                                    "link_count": len(links)
                                }
                                if error:
                                    meta["error"] = error
                                if images:
                                    meta["sample_images"] = images[:5]  # Store first 5 images
                                
                                # Safety guard: Truncate text to MEDIUMTEXT limit (16MB) to prevent DB errors
                                # MEDIUMTEXT max: 16,777,215 bytes (≈16 MB)
                                # Note: Truncation at 16MB is extremely rare - most web pages are <100KB
                                # If truncation occurs, it's likely mostly noise (ads, scripts, duplicate content)
                                MAX_TEXT_SIZE = 16_777_000  # Leave small buffer (≈16 MB)
                                
                                # Language detection and filtering
                                detected_language = None
                                safe_text = None
                                if text:
                                    # Detect language before processing
                                    try:
                                        from langdetect import detect, LangDetectException
                                        # Use first 1000 chars for faster detection
                                        sample_text = text[:1000] if len(text) > 1000 else text
                                        if len(sample_text.strip()) > 10:  # Need minimum text for detection
                                            detected_language = detect(sample_text)
                                            meta["detected_language"] = detected_language
                                            
                                            # Filter out non-English content
                                            if detected_language != 'en':
                                                logger.warning(f"🌐 Non-English content detected ({detected_language}) for {url}, filtering out")
                                                logger.warning(f"🌐 Sample text: {sample_text[:200]}...")
                                                meta["language_filtered"] = True
                                                meta["filter_reason"] = f"non_english_{detected_language}"
                                                safe_text = ""  # Skip non-English content
                                            else:
                                                logger.debug(f"✅ English content confirmed for {url}")
                                        else:
                                            logger.debug(f"⚠️ Text too short for language detection for {url}")
                                            meta["detected_language"] = "unknown"
                                    except LangDetectException as lang_err:
                                        logger.warning(f"⚠️ Language detection failed for {url}: {lang_err}")
                                        meta["detected_language"] = "unknown"
                                        meta["language_detection_error"] = str(lang_err)
                                    except ImportError:
                                        logger.warning("⚠️ langdetect not available - skipping language filtering")
                                        meta["detected_language"] = "not_checked"
                                    except Exception as lang_err:
                                        logger.warning(f"⚠️ Unexpected error in language detection for {url}: {lang_err}")
                                        meta["detected_language"] = "error"
                                    
                                    # Only process text if it's English (or if language detection failed/not available)
                                    if safe_text is None:  # Only process if not already filtered
                                        try:
                                            # Remove emojis and 4-byte UTF-8 characters (they cause DataError 1366)
                                            # Keep only 1-3 byte UTF-8 characters (basic unicode)
                                            safe_text = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                                            # Remove any remaining problematic characters (emojis are >0xFFFF)
                                            safe_text = ''.join(char for char in safe_text if ord(char) < 0x10000)
                                        except Exception as encode_err:
                                            logger.warning(f"⚠️ Error encoding extracted_text for {url}: {encode_err}, using empty string")
                                            safe_text = ""
                                        
                                        # Smart truncation: Keep first portion if too large
                                        if len(safe_text) > MAX_TEXT_SIZE:
                                            safe_text = safe_text[:MAX_TEXT_SIZE]
                                            logger.warning(f"⚠️ Truncated extracted_text for {url}: {len(text):,} chars → {len(safe_text):,} chars (exceeded MEDIUMTEXT 16MB limit)")
                                            logger.warning(f"⚠️ This is extremely rare - text >16MB likely contains mostly noise. First {MAX_TEXT_SIZE:,} chars preserved.")
                                            meta["text_truncated"] = True
                                            meta["original_length"] = len(text)
                                            meta["truncation_reason"] = "exceeded_mediumtext_limit"
                                else:
                                    safe_text = ""
                                
                                # Sanitize HTML to remove emojis/unicode that can't be stored in utf8mb3
                                # Keep only ASCII + basic UTF-8, remove 4-byte UTF-8 (emojis)
                                safe_html = None
                                if html and include_links:
                                    try:
                                        # Remove emojis and 4-byte UTF-8 characters (they cause DataError 1366)
                                        # Keep only 1-3 byte UTF-8 characters (basic unicode)
                                        safe_html = html[:MAX_TEXT_SIZE].encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                                        # Remove any remaining problematic characters
                                        safe_html = ''.join(char for char in safe_html if ord(char) < 0x10000)
                                    except Exception as encode_err:
                                        logger.warning(f"⚠️ Error encoding HTML for {url}: {encode_err}, storing as None")
                                        safe_html = None
                                
                                row = CampaignRawData(
                                    campaign_id=cid,
                                    source_url=url,
                                    fetched_at=now,
                                    raw_html=safe_html,  # Sanitized HTML (no emojis)
                                    extracted_text=safe_text if safe_text else (f"Error scraping {url}: {error}" if error else ""),
                                    meta_json=json.dumps(meta)
                                )
                                session.add(row)
                                # Flush to get DB ID immediately for logging
                                session.flush()
                                created += 1
                                
                                # Enhanced per-URL logging with DB ID
                                text_len = len(safe_text) if safe_text else 0
                                original_len = len(text) if text else 0
                                truncation_note = f" (truncated from {original_len})" if original_len > MAX_TEXT_SIZE else ""
                                
                                if error:
                                    logger.warning(f"⚠️ Scraped {url} (DB ID: {row.id}): ERROR - {error}")
                                else:
                                    logger.info(f"✅ Scraped {url} (DB ID: {row.id}): {text_len} chars{truncation_note}, {len(links)} links, {len(images)} images")
                            
                            logger.info(f"💾 Finished saving {len(scraped_results)} results to database (created={created} new, skipped={skipped_count} duplicates - reused existing data)")
                        except Exception as save_error:
                            logger.error(f"❌ CRITICAL: Error saving scraped data to database for campaign {cid}: {save_error}")
                            import traceback
                            logger.error(f"❌ Traceback: {traceback.format_exc()}")
                            # Continue anyway - we'll create an error row below
                        
                        # Only create error row if we haven't already created one (e.g., for Site Builder with 0 results)
                        if created == 0 and len(scraped_results) == 0:
                            logger.warning(f"⚠️ Web scraping returned no results for campaign {cid}")
                            # Create error row
                            row = CampaignRawData(
                                campaign_id=cid,
                                source_url="error:no_results",
                                fetched_at=now,
                                raw_html=None,
                                extracted_text=f"No results from web scraping. Keywords: {keywords}, URLs: {urls}",
                                meta_json=json.dumps({"type": "error", "reason": "no_scrape_results"})
                            )
                            session.add(row)
                            created = 1
                    
                    except Exception as scrape_error:
                        logger.error(f"❌ Web scraping failed for campaign {cid}: {scrape_error}")
                        import traceback
                        error_trace = traceback.format_exc()
                        logger.error(f"❌ Traceback: {error_trace}")
                        
                        # Check if this is a missing dependency error
                        error_msg = str(scrape_error)
                        if "No module named" in error_msg or "ImportError" in error_msg:
                            logger.error(f"❌ CRITICAL: Missing dependency detected: {error_msg}")
                            logger.error(f"❌ This will cause silent failures. Install missing packages immediately.")
                        
                        # Create error row with full error details
                        row = CampaignRawData(
                            campaign_id=cid,
                            source_url="error:scrape_failed",
                            fetched_at=now,
                            raw_html=None,
                            extracted_text=f"Web scraping error: {error_msg}",
                            meta_json=json.dumps({
                                "type": "error", 
                                "reason": "scrape_exception", 
                                "error": error_msg,
                                "traceback": error_trace[:500]  # Store first 500 chars of traceback
                            })
                        )
                        session.add(row)
                        created = 1
                
                if created > 0:
                    logger.info(f"💾 Committing {created} rows to database for campaign {cid}...")
                    set_task("scraping_complete", 75, f"Committing {created} rows to database...")
                    try:
                        session.commit()
                        logger.info(f"✅ Successfully committed {created} rows to database for campaign {cid}")
                        set_task("scraping_complete", 78, f"Database commit successful, verifying data...")
                    except Exception as commit_error:
                        # Check if campaign was deleted (foreign key constraint)
                        error_msg = str(commit_error).lower()
                        if "foreign key" in error_msg or "constraint" in error_msg or "campaign" in error_msg:
                            logger.error(f"❌ CRITICAL: Failed to save scraped data for campaign {cid} - campaign may have been deleted!")
                            logger.error(f"❌ Error: {commit_error}")
                            logger.error(f"❌ This usually happens when a campaign is deleted while scraping is in progress.")
                            logger.error(f"❌ {created} rows were scraped but could not be saved due to campaign deletion.")
                        else:
                            logger.error(f"❌ Failed to commit scraped data for campaign {cid}: {commit_error}")
                            import traceback
                            logger.error(f"❌ Traceback: {traceback.format_exc()}")
                        session.rollback()
                        # Don't re-raise - continue with analysis even if save failed
                    
                    # CRITICAL: Verify data was saved and check for valid (non-error) rows
                    all_saved_rows = session.query(CampaignRawData).filter(CampaignRawData.campaign_id == cid).all()
                    total_count = len(all_saved_rows)
                    valid_count = 0
                    error_count = 0
                    
                    total_text_size = 0
                    max_text_size = 0
                    
                    for row in all_saved_rows:
                        if row.source_url and row.source_url.startswith(("error:", "placeholder:")):
                            error_count += 1
                        else:
                            # Valid row - check if it has meaningful text
                            if row.extracted_text and len(row.extracted_text.strip()) > 10:
                                valid_count += 1
                                text_size = len(row.extracted_text)
                                total_text_size += text_size
                                max_text_size = max(max_text_size, text_size)
                                logger.debug(f"✅ Valid data row: {row.source_url} ({text_size} chars)")
                    
                    avg_text_size = total_text_size // valid_count if valid_count > 0 else 0
                    
                    logger.info(f"📊 Post-commit verification for campaign {cid}:")
                    logger.info(f"   Total rows: {total_count}")
                    logger.info(f"   Valid rows (with text): {valid_count}")
                    logger.info(f"   Error/placeholder rows: {error_count}")
                    logger.info(f"   Storage: {total_text_size:,} total chars, {avg_text_size:,} avg, {max_text_size:,} max")
                    
                    # Warn if approaching MEDIUMTEXT limit
                    if max_text_size > 15_000_000:
                        logger.warning(f"⚠️ Large page detected: {max_text_size:,} chars (close to MEDIUMTEXT 16MB limit)")
                    
                    # CRITICAL: If only error rows exist, log a warning
                    if valid_count == 0 and error_count > 0:
                        logger.error(f"❌ CRITICAL: Campaign {cid} has {error_count} error rows but 0 valid data rows!")
                        logger.error(f"❌ This indicates scraping failed. Check logs above for ImportError or missing dependencies.")
                        # Extract error messages for diagnostics
                        error_messages = []
                        for row in all_saved_rows:
                            if row.source_url and row.source_url.startswith(("error:", "placeholder:")):
                                error_text = row.extracted_text or row.source_url
                                if error_text not in error_messages:
                                    error_messages.append(error_text[:200])
                        if error_messages:
                            logger.error(f"❌ Error details from saved rows:")
                            for i, msg in enumerate(error_messages[:5], 1):
                                logger.error(f"   [{i}] {msg}")
                    elif valid_count == 0:
                        logger.warning(f"⚠️ Campaign {cid} has no rows saved at all - scraping may not have run")
                else:
                    logger.warning(f"⚠️ No rows to commit for campaign {cid}")

                # Step 3: processing content (scraping is already done, now just mark progress)
                logger.info(f"📊 Moving to processing_content step (80%) for campaign {cid}")
                set_task("processing_content", 80, f"Processing {created} scraped pages")
                logger.info(f"📊 Progress updated: 80% - processing_content")
                # Content is already processed during scraping, minimal delay
                time.sleep(2)

                # Step 3.5: Gap Analysis for Site Builder campaigns
                if data.type == "site_builder" and valid_count > 0:
                    try:
                        from gap_analysis import identify_content_gaps, rank_gaps_by_priority
                        from text_processing import extract_topics
                        
                        logger.info(f"🏗️ Site Builder: Starting gap analysis for campaign {cid}")
                        set_task("gap_analysis", 70, "Analyzing content gaps")
                        
                        # Get scraped texts for topic extraction
                        all_rows = session.query(CampaignRawData).filter(
                            CampaignRawData.campaign_id == cid,
                            ~CampaignRawData.source_url.startswith(("error:", "placeholder:"))
                        ).all()
                        
                        texts = [row.extracted_text for row in all_rows if row.extracted_text and len(row.extracted_text.strip()) > 50]
                        
                        if texts:
                            # Extract topics from existing content
                            logger.info(f"🔍 Extracting topics from {len(texts)} pages...")
                            existing_topics = extract_topics(
                                texts=texts,
                                topic_tool="system",  # Use system model for speed
                                num_topics=20,
                                iterations=25,
                                query=data.query or "",
                                keywords=[],
                                urls=[]
                            )
                            logger.info(f"✅ Extracted {len(existing_topics)} topics from site content")
                            
                            # Build knowledge graph structure from existing topics
                            # (Simplified - full KG would come from research endpoint)
                            existing_kg = {
                                "nodes": [{"id": t.lower(), "label": t} for t in existing_topics[:50]],
                                "edges": []  # Simplified - full edges would come from research endpoint
                            }
                            
                            # Perform gap analysis
                            target_keywords = getattr(data, 'target_keywords', None) or data.keywords or []
                            if target_keywords:
                                gaps = identify_content_gaps(
                                    existing_topics=existing_topics,
                                    knowledge_graph=existing_kg,
                                    target_keywords=target_keywords,
                                    existing_urls=[row.source_url for row in all_rows[:100]]
                                )
                                
                                # Rank and filter gaps
                                top_ideas_count = getattr(data, 'top_ideas_count', 10)
                                top_gaps = rank_gaps_by_priority(gaps, top_n=top_ideas_count)
                                
                                logger.info(f"✅ Gap analysis complete: {len(gaps)} total gaps, {len(top_gaps)} top priority gaps")
                                
                                # Store gap analysis results in campaign
                                camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                                if camp:
                                    camp.gap_analysis_results_json = json.dumps({
                                        "total_gaps": len(gaps),
                                        "top_gaps": top_gaps,
                                        "existing_topics": existing_topics[:50],
                                        "target_keywords": target_keywords,
                                        "coverage_score": len([g for g in gaps if g.get("priority") == "high"]) / len(gaps) if gaps else 0
                                    })
                                    camp.site_base_url = site_url
                                    camp.target_keywords_json = json.dumps(target_keywords)
                                    camp.top_ideas_count = top_ideas_count
                                    session.commit()
                                    logger.info(f"✅ Saved gap analysis results to campaign {cid}")
                            else:
                                logger.warning(f"⚠️ No target keywords provided for gap analysis")
                        else:
                            logger.warning(f"⚠️ No valid text content found for gap analysis")
                    except Exception as gap_error:
                        logger.error(f"❌ Gap analysis failed: {gap_error}")
                        import traceback
                        logger.error(traceback.format_exc())

                # Step 4: extracting entities
                set_task("extracting_entities", 75, "Extracting entities from scraped content")
                # Entities will be extracted when research endpoint is called
                time.sleep(2)

                # Step 5: modeling topics (only if we have data)
                if created > 0:
                    set_task("modeling_topics", 90, "Preparing content for analysis")
                    # Topics will be modeled when research endpoint is called
                    time.sleep(2)
                else:
                    set_task("modeling_topics", 90, "Waiting for scraping to complete...")
                    # Wait a bit longer if no data yet (scraping might still be running)
                    time.sleep(5)

                # Mark campaign ready in DB - validate data BEFORE setting progress to 100%
                logger.info(f"📝 Step 6: Finalizing campaign {cid}")
                try:
                    # Use a fresh query to ensure we get the latest campaign state
                    camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                    if camp:
                        logger.info(f"📝 Found campaign {cid} in database, updating status...")
                        logger.info(f"📝 Current status: {camp.status}, current topics: {camp.topics}")
                        
                        # Check if we have scraped data before marking as ready
                        # IMPORTANT: Only count valid scraped data (exclude error/placeholder rows)
                        all_rows = session.query(CampaignRawData).filter(CampaignRawData.campaign_id == cid).all()
                        valid_data_count = 0
                        valid_text_count = 0
                        error_count = 0
                        
                        for row in all_rows:
                            if row.source_url and row.source_url.startswith(("error:", "placeholder:")):
                                error_count += 1
                                logger.debug(f"⚠️ Skipping error/placeholder row: {row.source_url}")
                            else:
                                # Valid scraped data - check if it has meaningful content
                                if row.source_url and row.extracted_text and len(row.extracted_text.strip()) > 10:
                                    valid_data_count += 1
                                    valid_text_count += 1
                                    logger.debug(f"✅ Valid data row: {row.source_url} ({len(row.extracted_text)} chars)")
                                elif row.source_url:
                                    # Has URL but no/minimal text - DON'T count as valid (frontend can't use it)
                                    # This prevents false-positive READY_TO_ACTIVATE status
                                    logger.debug(f"⚠️ Skipping row with URL but no/minimal text: {row.source_url} (text length: {len(row.extracted_text or '')})")
                                    # Don't increment valid_data_count - this row is not usable
                        
                        logger.info(f"📊 Data validation: {valid_data_count} valid rows, {valid_text_count} with text, {error_count} error/placeholder rows")
                        
                        # CRITICAL: Check if all URLs were already scraped (100% duplicates = no changes)
                        # This happens when a campaign is re-scraped but all URLs already exist in the database
                        all_urls_were_duplicates = (
                            total_urls_scraped > 0 and 
                            skipped_count > 0 and 
                            created == 0 and 
                            skipped_count == total_urls_scraped
                        )
                        
                        if all_urls_were_duplicates and valid_data_count > 0:
                            # All URLs were already scraped - no changes detected
                            logger.info(f"🔄 Campaign {cid} re-scraped but all {skipped_count} URLs were already in database - no changes detected")
                            
                            # Store coarse topics from keywords as a ready signal (if not already set)
                            if (data.keywords or []) and not camp.topics:
                                camp.topics = ",".join((data.keywords or [])[:10])
                                logger.info(f"📝 Set topics to: {camp.topics}")
                            
                            # Set status to NO_CHANGES to indicate re-run with no new data
                            camp.status = "NO_CHANGES"
                            camp.updated_at = datetime.utcnow()
                            session.commit()
                            logger.info(f"✅ Campaign {cid} marked as NO_CHANGES - re-scraped but all {skipped_count} URLs already existed (reused existing data)")
                            
                            # Set progress to 100% to indicate completion
                            set_task("finalizing", 100, f"Re-scraped - all {skipped_count} URLs already existed, no changes detected")
                            
                            # Verify the status was saved correctly
                            session.refresh(camp)
                            if camp.status != "NO_CHANGES":
                                logger.error(f"❌ CRITICAL: Campaign {cid} status was not saved correctly! Expected NO_CHANGES, got {camp.status}")
                                # Force update again
                                camp.status = "NO_CHANGES"
                                camp.updated_at = datetime.utcnow()
                                session.commit()
                                logger.info(f"🔧 Force-updated campaign {cid} status to NO_CHANGES")
                        # For Site Builder campaigns, require at least some valid data
                        elif data.type == "site_builder" and valid_data_count == 0:
                            logger.error(f"❌ Site Builder campaign {cid} has no valid scraped data!")
                            logger.error(f"❌ Total rows: {len(all_rows)}, Error rows: {error_count}")
                            if error_count > 0:
                                logger.error(f"❌ This indicates sitemap parsing or scraping failed. Check error rows above.")
                            camp.status = "INCOMPLETE"
                            camp.updated_at = datetime.utcnow()
                            session.commit()
                            logger.error(f"❌ Campaign {cid} status set to INCOMPLETE due to no valid data")
                            
                            # CRITICAL: Verify the status was saved correctly
                            session.refresh(camp)
                            if camp.status != "INCOMPLETE":
                                logger.error(f"❌ CRITICAL: Campaign {cid} status was not saved correctly! Expected INCOMPLETE, got {camp.status}")
                                # Force update again
                                camp.status = "INCOMPLETE"
                                camp.updated_at = datetime.utcnow()
                                session.commit()
                                logger.info(f"🔧 Force-updated campaign {cid} status to INCOMPLETE")
                            else:
                                logger.info(f"✅ Verified campaign {cid} status is INCOMPLETE in database")
                            
                            # Keep progress at 95% to indicate it's not fully complete
                            set_task("error", 95, "Scraping completed but no valid data found. Check logs for details.")
                        elif valid_data_count > 0:
                            # Store coarse topics from keywords as a ready signal
                            if (data.keywords or []) and not camp.topics:
                                camp.topics = ",".join((data.keywords or [])[:10])
                                logger.info(f"📝 Set topics to: {camp.topics}")
                            
                            # CRITICAL: Set status to READY_TO_ACTIVATE and commit immediately
                            camp.status = "READY_TO_ACTIVATE"
                            camp.updated_at = datetime.utcnow()
                            session.commit()
                            logger.info(f"✅ Campaign {cid} marked as READY_TO_ACTIVATE with {valid_data_count} valid data rows ({valid_text_count} with text)")
                            # Scrape writes only to CampaignRawData. Queue = user-selected ideas from Research Assistant only (see CAMPAIGN_FLOW_RAW_DATA_TO_CONTENT).
                            # Only set progress to 100% AFTER we've confirmed valid data exists
                            set_task("finalizing", 100, f"Scraping complete - {valid_data_count} pages scraped successfully")
                            
                            # Verify the status was saved correctly
                            session.refresh(camp)
                            if camp.status != "READY_TO_ACTIVATE":
                                logger.error(f"❌ CRITICAL: Campaign {cid} status was not saved correctly! Expected READY_TO_ACTIVATE, got {camp.status}")
                                # Force update again
                                camp.status = "READY_TO_ACTIVATE"
                                session.commit()
                                logger.info(f"🔧 Force-updated campaign {cid} status to READY_TO_ACTIVATE")
                        else:
                            # No valid scraped data - check if we have errors
                            if error_count > 0:
                                logger.error(f"❌ Campaign {cid} scraping failed: {error_count} error rows, 0 valid data rows")
                                logger.error(f"❌ This indicates scraping did not succeed. Check logs above for scraping errors.")
                                # Keep progress at 95% to indicate failure - NEVER set to 100% if no valid data
                                set_task("error", 95, f"Scraping failed: {error_count} errors, 0 valid data. Check logs for details.")
                                
                                # Extract error messages from error rows for better diagnostics
                                error_messages = []
                                missing_deps = []
                                for row in all_rows:
                                    if row.source_url and row.source_url.startswith(("error:", "placeholder:")):
                                        error_msg = row.extracted_text or row.source_url
                                        if error_msg not in error_messages:
                                            error_messages.append(error_msg[:200])  # Limit length
                                        # Check for missing dependency errors
                                        if "No module named" in error_msg or "ImportError" in error_msg:
                                            missing_deps.append(error_msg)
                                
                                if missing_deps:
                                    logger.error(f"❌ CRITICAL: Missing dependencies detected:")
                                    for dep_error in missing_deps:
                                        logger.error(f"   - {dep_error[:150]}")
                                    logger.error(f"❌ Fix: Run './scripts/fix_missing_deps_now.sh' or 'pip install beautifulsoup4 gensim'")
                                
                                if error_messages:
                                    logger.error(f"❌ Error details from database:")
                                    for i, msg in enumerate(error_messages[:5], 1):  # Show first 5
                                        logger.error(f"   [{i}] {msg}")
                                
                                logger.error(f"❌ Common causes:")
                                logger.error(f"   1. Missing dependencies (bs4, gensim): Run 'pip install beautifulsoup4 gensim'")
                                logger.error(f"   2. Playwright not installed: Run 'python -m playwright install chromium'")
                                logger.error(f"   3. DuckDuckGo search failing: Check 'ddgs' package is installed")
                                logger.error(f"   4. Network/firewall blocking: Check server can access external URLs")
                                logger.error(f"   5. Invalid keywords: Empty or malformed keywords return no results")
                                
                                # Set status with diagnostic message
                                camp.status = "INCOMPLETE"
                                if missing_deps:
                                    camp.description = (camp.description or "") + f"\n[ERROR: Missing dependencies - check logs]"
                            else:
                                # No rows at all - this shouldn't happen but handle it
                                logger.error(f"❌ Campaign {cid} has no data rows at all (no errors, no valid data)")
                                logger.error(f"❌ This suggests scraping never ran or failed before creating any rows")
                                # Keep progress at 95% to indicate failure
                                set_task("error", 95, "No data was scraped. Check backend logs for details.")
                            
                            # Set status to INCOMPLETE for all failure cases
                            logger.info(f"🔧 Setting campaign {cid} status to INCOMPLETE (no valid data)")
                            camp.status = "INCOMPLETE"
                            camp.updated_at = datetime.utcnow()
                            try:
                                session.commit()
                                logger.info(f"✅ Campaign {cid} status committed to database as INCOMPLETE")
                            except Exception as commit_err:
                                logger.error(f"❌ CRITICAL: Failed to commit INCOMPLETE status for campaign {cid}: {commit_err}")
                                import traceback
                                logger.error(f"❌ Commit error traceback:\n{traceback.format_exc()}")
                                session.rollback()
                                # Try one more time
                                try:
                                    camp.status = "INCOMPLETE"
                                    camp.updated_at = datetime.utcnow()
                                    session.commit()
                                    logger.info(f"🔧 Retry: Campaign {cid} status committed to database as INCOMPLETE")
                                except Exception as retry_err:
                                    logger.error(f"❌ CRITICAL: Retry commit also failed for campaign {cid}: {retry_err}")
                            
                            # CRITICAL: Verify the status was saved correctly (same as READY_TO_ACTIVATE path)
                            try:
                                session.refresh(camp)
                                if camp.status != "INCOMPLETE":
                                    logger.error(f"❌ CRITICAL: Campaign {cid} status was not saved correctly! Expected INCOMPLETE, got {camp.status}")
                                    # Force update again
                                    camp.status = "INCOMPLETE"
                                    camp.updated_at = datetime.utcnow()
                                    session.commit()
                                    logger.info(f"🔧 Force-updated campaign {cid} status to INCOMPLETE")
                                else:
                                    logger.info(f"✅ Verified campaign {cid} status is INCOMPLETE in database")
                            except Exception as verify_err:
                                logger.error(f"❌ CRITICAL: Failed to verify INCOMPLETE status for campaign {cid}: {verify_err}")
                                import traceback
                                logger.error(f"❌ Verify error traceback:\n{traceback.format_exc()}")
                    else:
                        logger.warning(f"⚠️ Campaign {cid} not found in database when trying to finalize")
                except Exception as finalize_err:
                    logger.error(f"❌ Error finalizing campaign {cid}: {finalize_err}")
                    import traceback
                    logger.error(traceback.format_exc())
                    session.rollback()
                    # Try to set status to INCOMPLETE as fallback
                    try:
                        camp = session.query(Campaign).filter(Campaign.campaign_id == cid).first()
                        if camp:
                            camp.status = "INCOMPLETE"
                            camp.updated_at = datetime.utcnow()
                            session.commit()
                            logger.info(f"⚠️ Set campaign {cid} to INCOMPLETE due to finalization error")
                    except:
                        pass
                    
                logger.info(f"✅ Background analysis completed successfully for campaign {cid}")
            except Exception as e:
                import traceback
                logger.error(f"❌ Background analysis error for campaign {cid}: {e}")
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
            finally:
                session.close()
                logger.info(f"🔵 Background thread finished for task {tid}, campaign {cid}")

        # Start background thread
        # Convert Pydantic model to dict to avoid serialization issues when passing to thread
        try:
            logger.info(f"🔍 About to start background thread for task {task_id}")
            # Convert analyze_data to dict for thread safety
            try:
                # Try Pydantic v2 method first
                if hasattr(analyze_data, 'model_dump'):
                    analyze_data_dict = analyze_data.model_dump()
                    logger.info(f"🔍 Used model_dump() to convert to dict")
                # Fallback to Pydantic v1 method
                elif hasattr(analyze_data, 'dict'):
                    analyze_data_dict = analyze_data.dict()
                    logger.info(f"🔍 Used dict() to convert to dict")
                else:
                    # Last resort: manual conversion
                    analyze_data_dict = {
                        'campaign_id': getattr(analyze_data, 'campaign_id', None),
                        'campaign_name': getattr(analyze_data, 'campaign_name', None),
                        'type': getattr(analyze_data, 'type', 'keyword'),
                        'site_base_url': getattr(analyze_data, 'site_base_url', None),
                        'target_keywords': getattr(analyze_data, 'target_keywords', None),
                        'top_ideas_count': getattr(analyze_data, 'top_ideas_count', 10),
                        'most_recent_urls': getattr(analyze_data, 'most_recent_urls', None),
                        'keywords': getattr(analyze_data, 'keywords', []),
                        'urls': getattr(analyze_data, 'urls', []),
                        'description': getattr(analyze_data, 'description', None),
                        'query': getattr(analyze_data, 'query', None),
                    }
                    logger.info(f"🔍 Used manual conversion to dict")
                logger.info(f"🔍 Converted analyze_data to dict, keys: {list(analyze_data_dict.keys())}")
            except Exception as dict_error:
                logger.error(f"❌ CRITICAL: Failed to convert analyze_data to dict: {dict_error}")
                import traceback
                logger.error(f"❌ Dict conversion traceback: {traceback.format_exc()}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to prepare analysis data: {str(dict_error)}"
                )
            
            # Reconstruct AnalyzeRequest from dict in the background thread
            thread = threading.Thread(target=run_analysis_background, args=(task_id, campaign_id, analyze_data_dict), daemon=True)
            thread.start()
            logger.info(f"✅ Background thread started successfully for task {task_id}")
        except Exception as thread_error:
            logger.error(f"❌ CRITICAL: Failed to start background thread: {thread_error}")
            import traceback
            logger.error(f"❌ Thread start traceback: {traceback.format_exc()}")
            # Remove task from CONTENT_GEN_TASKS since thread failed to start
            if task_id in CONTENT_GEN_TASKS:
                del CONTENT_GEN_TASKS[task_id]
            if campaign_id in CONTENT_GEN_TASK_INDEX:
                raw = CONTENT_GEN_TASK_INDEX[campaign_id]
                if isinstance(raw, list):
                    new_list = [tid for tid in raw if tid != task_id]
                    if new_list:
                        CONTENT_GEN_TASK_INDEX[campaign_id] = new_list
                    else:
                        del CONTENT_GEN_TASK_INDEX[campaign_id]
                elif raw == task_id:
                    del CONTENT_GEN_TASK_INDEX[campaign_id]
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start analysis thread: {str(thread_error)}"
            )

        return {
            "status": "started",
            "task_id": task_id,
            "message": "Analysis started",
            "campaign_id": campaign_id,
            "campaign_name": campaign_name
        }
    except HTTPException:
        # Re-raise HTTP exceptions (like 400, 404) as-is
        raise
    except Exception as e:
        import traceback
        from pydantic import ValidationError
        error_trace = traceback.format_exc()
        logger.error(f"❌ CRITICAL: Error in /analyze endpoint: {str(e)}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        logger.error(f"❌ Full traceback:\n{error_trace}")
        # Log the request data for debugging
        try:
            logger.error(f"❌ Request data: campaign_id={analyze_data.campaign_id}, type={analyze_data.type}, site_base_url={getattr(analyze_data, 'site_base_url', None)}")
        except:
            pass
        
        # Handle ValidationError specifically
        if isinstance(e, ValidationError):
            logger.error(f"❌ Pydantic ValidationError: {e.errors()}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "status": "error",
                    "message": "Validation error in request data",
                    "errors": e.errors(),
                    "error_type": "ValidationError"
                }
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": f"Failed to start analysis: {str(e)}",
                "error_type": type(e).__name__
            }
        )

@content_generation_router.get("/analyze/status/{task_id}")
def get_analyze_status(task_id: str, current_user = Depends(get_current_user)):
    """
    Get analysis status - In-memory progress simulation.
    Progress advances deterministically based on time since start.
    REQUIRES AUTHENTICATION
    """
    # Verify task belongs to user (check campaign ownership)
    if task_id in CONTENT_GEN_TASKS:
        task_campaign_id = CONTENT_GEN_TASKS[task_id].get("campaign_id")
        if task_campaign_id:
            from models import Campaign
            from database import SessionLocal
            session = SessionLocal()
            try:
                campaign = session.query(Campaign).filter(
                    Campaign.campaign_id == task_campaign_id,
                    Campaign.user_id == current_user.id
                ).first()
                if not campaign:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Task not found or access denied"
                    )
            finally:
                session.close()
    
    if task_id not in CONTENT_GEN_TASKS:
        # Be resilient across restarts: report pending instead of 404 so UI keeps polling
        return {
            "status": "pending",
            "progress": 5,
            "current_step": "initializing",
            "progress_message": "Waiting for task",
            "campaign_id": None,
        }
    
    task = CONTENT_GEN_TASKS[task_id]
    
    # CRITICAL: Return REAL progress if it's been set (from scraping, etc.)
    # Only use time-based simulation if real progress hasn't been set yet
    real_progress = task.get("progress")
    real_step = task.get("current_step")
    real_message = task.get("progress_message")
    
    # CRITICAL: If real_progress has been set (even if 0), use it
    # This ensures we return progress even when it's 0 initially
    if real_progress is not None and real_step:
        # Real progress has been set (e.g., during scraping)
        progress = real_progress
        current_step = real_step
        progress_message = real_message or f"{current_step.replace('_',' ').title()}"
        
        # Determine status based on progress
        if progress >= 100:
            status = "completed"
        elif progress > 0:
            status = "in_progress"
        else:
            status = "pending"
        
        logger.debug(f"📊 Returning REAL progress for task {task_id}: {progress}% - {current_step} - {progress_message}")
        return {
            "status": status,
            "progress": progress,
            "current_step": current_step,
            "progress_message": progress_message,
            "campaign_id": task["campaign_id"],
        }
    
    # Fallback: Compute time-based progress (only if real progress not set yet)
    try:
        from datetime import datetime as dt
        started = dt.fromisoformat(task["started_at"])  # UTC naive ISO ok
        elapsed = (dt.utcnow() - started).total_seconds()
    except Exception:
        elapsed = 0
    
    # Step thresholds (seconds -> progress, step label)
    steps = [
        (0,   5,  "initializing"),
        (5,  15,  "collecting_inputs"),
        (10, 25,  "fetching_content"),
        (20, 50,  "processing_content"),
        (30, 70,  "extracting_entities"),
        (40, 85,  "modeling_topics"),
        (45, 100, "finalizing"),
    ]
    progress = 5
    current_step = "initializing"
    for threshold, prog, step in steps:
        if elapsed >= threshold:
            progress = prog
            current_step = step
        else:
            break
    
    # Only update if real progress wasn't set
    if real_progress is None:
        task["progress"] = progress
        task["current_step"] = current_step
        task["progress_message"] = f"{current_step.replace('_',' ').title()}"
    
    # Use real progress if available, otherwise use time-based
    final_progress = real_progress if real_progress is not None else progress
    final_step = real_step if real_step else current_step
    final_message = real_message if real_message else f"{current_step.replace('_',' ').title()}"
    
    return {
        "status": "in_progress" if final_progress < 100 else "completed",
        "progress": final_progress,
        "current_step": final_step,
        "progress_message": final_message,
        "campaign_id": task["campaign_id"],
    }

# Optional helper: get status by campaign_id
@content_generation_router.get("/analyze/status/by_campaign/{campaign_id}")
def get_status_by_campaign(campaign_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get analysis status by campaign ID - REQUIRES AUTHENTICATION AND OWNERSHIP VERIFICATION"""
    # Verify campaign ownership
    from models import Campaign
    campaign = db.query(Campaign).filter(
        Campaign.campaign_id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found or access denied"
        )
    
    # CRITICAL: Find the ACTIVE task for this campaign (not just the one in index)
    # Multiple tasks might exist if Build button was clicked multiple times
    # Return the one that's actually running (in_progress), or the most recent one
    
    active_task_id = None
    active_task_progress = -1
    
    # First check the index (most recent task); index can be list (multiple tasks per campaign) or legacy single task_id
    raw_index = CONTENT_GEN_TASK_INDEX.get(campaign_id)
    index_list = raw_index if isinstance(raw_index, list) else ([raw_index] if raw_index else [])
    
    # Check all tasks to find the one that's actually running
    for tid, task in CONTENT_GEN_TASKS.items():
        if task.get("campaign_id") == campaign_id:
            task_progress = task.get("progress", 0)
            # Prefer tasks that are actively running (progress > 0 and < 100)
            if 0 < task_progress < 100:
                if task_progress > active_task_progress:
                    active_task_id = tid
                    active_task_progress = task_progress
            # If no active task found yet, use the one from index
            elif active_task_id is None and tid in index_list:
                active_task_id = tid
    
    # Fallback to index if no active task found (use first from list)
    if not active_task_id and index_list:
        active_task_id = index_list[0] if index_list else None
    
    if not active_task_id or active_task_id not in CONTENT_GEN_TASKS:
        # Task doesn't exist - return a clear status instead of 404
        # This happens if server restarted or analysis never started
        return {
            "status": "not_found",
            "progress": 0,
            "current_step": "not_started",
            "progress_message": "Analysis task not found. The campaign may not have started analysis yet, or the server was restarted. Try clicking 'Build Campaign' again.",
            "campaign_id": campaign_id
        }
    
    logger.debug(f"📊 get_status_by_campaign: Using task {active_task_id} for campaign {campaign_id} (index had {raw_index})")
    return get_analyze_status(active_task_id, current_user)

# Debug endpoint to check raw data for a campaign
@content_generation_router.post("/generate-ideas")
async def generate_ideas_endpoint(
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate content ideas based on topics, posts, and days.
    Used by content queue flow after selecting platforms and number of posts.
    Accepts form-urlencoded data: topics, posts, days
    REQUIRES AUTHENTICATION
    """
    try:
        from machine_agent import IdeaGeneratorAgent
        from langchain_openai import ChatOpenAI
        from fastapi import Form
        
        api_key = get_openai_api_key(current_user=current_user, db=db)
        if not api_key:
            return {"status": "error", "message": "OpenAI API key not configured. Please set a global key in Admin Settings > System > Platform Keys, or add your personal key in Account Settings."}
        
        # Parse form data from request
        form_data = await request.form()
        topics = form_data.get("topics", "")
        posts = form_data.get("posts", "")
        days = form_data.get("days", "")
        num_ideas_str = form_data.get("num_ideas", "")
        recommendations = form_data.get("recommendations", "")  # New: recommendations context
        
        # Parse topics, posts, and days from form data
        topics_list = []
        if topics:
            # Topics come as: "Topic A" , "Topic B"
            # Remove quotes and split by comma
            topics_list = [t.strip().strip('"').strip("'") for t in topics.split(",") if t.strip()]
        
        posts_list = []
        if posts:
            # Posts come as: "Your post here"
            posts_list = [posts.strip().strip('"').strip("'")]
        
        days_list = []
        if days:
            # Days come as: Monday, Tuesday
            days_list = [d.strip() for d in days.split(",") if d.strip()]
        
        # Parse num_ideas - use provided value or fall back to days count
        try:
            num_ideas = int(num_ideas_str) if num_ideas_str else len(days_list) if days_list else 1
        except ValueError:
            num_ideas = len(days_list) if days_list else 1
        
        # If we have recommendations but no topics, extract topics from recommendations
        if not topics_list and recommendations:
            # Extract keywords from recommendations (look for bold text, quoted text, etc.)
            import re
            # Extract **bold** text
            bold_keywords = re.findall(r'\*\*([^*]+)\*\*', recommendations)
            # Extract "quoted" text
            quoted_keywords = re.findall(r'"([^"]+)"', recommendations)
            # Extract capitalized phrases (potential topics)
            capitalized = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', recommendations)
            topics_list = list(set(bold_keywords + quoted_keywords + capitalized[:5]))  # Limit capitalized to avoid noise
        
        # If still no topics, try to extract from posts
        if not topics_list and posts_list:
            # Use the post content as a topic if available
            topics_list = [post[:100] for post in posts_list if post.strip()]  # Use first 100 chars of post as topic
        
        # If still no topics, allow proceeding with a generic topic
        # This allows users to proceed with content creation even if topics weren't explicitly provided
        # The selected items from ContentQueue/ResearchAssistant should be sufficient
        if not topics_list:
            # Use a generic topic to allow the process to continue
            # The user has already selected items, so we should proceed
            topics_list = ["Content creation"]  # Generic fallback to allow proceeding
            logger.info("⚠️ No explicit topics provided, using generic fallback to allow content creation to proceed")
        
        if num_ideas < 1:
            return {"status": "error", "message": "Number of ideas must be at least 1"}
        
        # Initialize LLM and agent
        llm = ChatOpenAI(model=get_openai_default_model(), api_key=api_key.strip(), temperature=0.7)
        agent = IdeaGeneratorAgent(llm, db_session=db)
        
        # Generate ideas - pass num_ideas and recommendations context
        ideas = await agent.generate_ideas(topics_list, posts_list, days_list, num_ideas=num_ideas, recommendations=recommendations)
        
        if not ideas or len(ideas) == 0:
            return {"status": "error", "message": "Failed to generate ideas"}
        
        logger.info(f"✅ Generated {len(ideas)} content ideas")
        
        # Return same format as original implementation
        return {
            "status": "success",
            "ideas": ideas
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating content ideas: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to generate ideas: {str(e)}")

@content_generation_router.post("/campaigns/{campaign_id}/generate-content/force-complete/{task_id}")
async def force_complete_content_generation(
    campaign_id: str,
    task_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Force complete a hung content generation task.
    Marks all running agents as error and sets task status to error.
    """
    try:
        from models import Campaign
        
        # Verify campaign ownership
        campaign = db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if task_id not in CONTENT_GEN_TASKS:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = CONTENT_GEN_TASKS[task_id]
        
        # Mark all running agents as error
        if "agent_statuses" in task:
            for agent_status in task["agent_statuses"]:
                if agent_status.get("status") == "running":
                    agent_status["status"] = "error"
                    agent_status["agent_status"] = "error"
                    agent_status["error"] = "Force completed by user - agent was hung"
                    agent_status["task"] = f"{agent_status.get('task', 'Processing')} - FORCE COMPLETED"
        
        # Set task status to error
        task["status"] = "error"
        task["error"] = "Task force completed due to hung agents"
        task["current_agent"] = None
        task["current_task"] = "Task force completed - agents were hung"
        task["progress"] = task.get("progress", 0)
        
        logger.warning(f"⚠️ Task {task_id} force completed by user {current_user.id}")
        
        return {
            "status": "error",
            "message": "Task force completed",
            "task_id": task_id
        }
        
    except Exception as e:
        logger.error(f"Error force completing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Image Generation Endpoint
@content_generation_router.post("/generate_image_machine_content")
async def generate_image_machine_content_endpoint(
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate an image for machine content using DALL·E.
    Accepts POST with body: { id, query (article content), image_settings (optional) }
    Also accepts GET with query params: ?id=...&query=...
    
    The prompt is built by:
    1. Using the article content (query) to determine what the image should depict
    2. Incorporating image settings (style, color, additional prompt) to style the image
    """
    try:
        # Try to get data from POST body first
        try:
            body = await request.json()
            content_id = body.get("id")
            article_content = body.get("query")  # This is the article content/summary
            image_settings = body.get("image_settings") or body.get("imageSettings")
        except:
            # Fallback to query params (for GET requests)
            content_id = request.query_params.get("id")
            article_content = request.query_params.get("query")
            image_settings = None
        
        if not content_id or not article_content:
            raise HTTPException(
                status_code=400,
                detail="Missing required parameters: 'id' and 'query' (article content) are required"
            )
        
        # Import image generation function
        try:
            from tools import generate_image
        except ImportError:
            logger.error("Could not import generate_image from tools")
            raise HTTPException(
                status_code=500,
                detail="Image generation service not available"
            )
        
        # Build the image prompt:
        # 1. Extract key visual elements from article content (what the image should show)
        # 2. Apply image settings (style, color, additional prompt) to style it
        
        # Start with article content - this determines WHAT the image depicts
        # Extract a summary or key visual concept from the article
        article_summary = article_content[:500] if len(article_content) > 500 else article_content
        
        # Get Global Image Agent prompt - ALWAYS use it for image generation
        global_image_agent_prompt = ""
        try:
            from models import SystemSettings
            # Try to get the Global Image Agent prompt
            global_agent_setting = db.query(SystemSettings).filter(
                SystemSettings.setting_key == "creative_agent_global_image_agent_prompt"
            ).first()
            if global_agent_setting and global_agent_setting.setting_value:
                global_image_agent_prompt = global_agent_setting.setting_value
            else:
                # Fallback: use default prompt if Global Image Agent not configured yet
                global_image_agent_prompt = "Create visually compelling images that align with the content's message and tone. Ensure images are professional, on-brand, and enhance the overall content experience."
                logger.info("Using default Global Image Agent prompt (agent not yet configured)")
        except Exception as e:
            logger.warning(f"Could not fetch Global Image Agent prompt: {e}")
            # Fallback to default prompt
            global_image_agent_prompt = "Create visually compelling images that align with the content's message and tone. Ensure images are professional, on-brand, and enhance the overall content experience."
        
        # Get additional creative agent prompt if selected
        additional_creative_agent_prompt = ""
        if image_settings:
            additional_agent_id = image_settings.get("additionalCreativeAgentId")
            logger.info(f"🎨 Image settings received: {image_settings}")
            logger.info(f"🎨 Additional Creative Agent ID: {additional_agent_id}")
            if additional_agent_id:
                try:
                    from models import SystemSettings
                    setting_key = f"creative_agent_{additional_agent_id}_prompt"
                    logger.info(f"🔍 Looking for creative agent prompt with key: {setting_key}")
                    additional_agent_setting = db.query(SystemSettings).filter(
                        SystemSettings.setting_key == setting_key
                    ).first()
                    if additional_agent_setting:
                        logger.info(f"✅ Found creative agent setting: {setting_key}")
                        if additional_agent_setting.setting_value:
                            additional_creative_agent_prompt = additional_agent_setting.setting_value
                            logger.info(f"✅ Creative agent prompt loaded ({len(additional_creative_agent_prompt)} chars): {additional_creative_agent_prompt[:200]}...")
                        else:
                            logger.warning(f"⚠️ Creative agent setting found but setting_value is empty for {setting_key}")
                    else:
                        logger.warning(f"⚠️ Creative agent setting NOT FOUND for key: {setting_key}")
                        # Log all available creative agent settings for debugging
                        all_creative_agents = db.query(SystemSettings).filter(
                            SystemSettings.setting_key.like("creative_agent_%_prompt")
                        ).all()
                        logger.info(f"📋 Available creative agent prompts: {[s.setting_key for s in all_creative_agents]}")
                except Exception as e:
                    logger.error(f"❌ Could not fetch additional creative agent prompt: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.info("ℹ️ No additionalCreativeAgentId provided in image_settings")
        
        # Build style components from image settings
        style_components = []
        if image_settings:
            style = image_settings.get("style", "")
            color = image_settings.get("color", "")
            additional_prompt = image_settings.get("prompt", "") or image_settings.get("additionalPrompt", "")
            
            if style:
                style_components.append(f"in {style} style")
            if color:
                style_components.append(f"with {color} color palette")
            if additional_prompt:
                style_components.append(additional_prompt)
        
        # Combine: Article content (what) + Global Image Agent prompt + Additional Creative Agent prompt + Image settings (how)
        # IMPORTANT: Custom creative agent prompt should be prominent and early in the prompt
        prompt_parts = []
        
        # Start with article summary (what the image should show)
        prompt_parts.append(article_summary)
        
        # Add Additional Creative Agent prompt EARLY and PROMINENTLY if available
        # This ensures DALL-E pays attention to the custom agent's instructions
        if additional_creative_agent_prompt:
            prompt_parts.append(f"IMPORTANT: Apply this creative direction: {additional_creative_agent_prompt}")
            logger.info(f"✅ Custom creative agent prompt INCLUDED prominently in final prompt")
        else:
            logger.info(f"ℹ️ No custom creative agent prompt to include")
        
        # ALWAYS add Global Image Agent prompt (it has a fallback default if not configured)
        prompt_parts.append(f"Follow these guidelines: {global_image_agent_prompt}")
        
        # Add style components
        if style_components:
            prompt_parts.append(f"Create an image {', '.join(style_components)}.")
        else:
            prompt_parts.append("Create a relevant image.")
        
        final_prompt = ". ".join(prompt_parts) + "."
        
        logger.info(f"🖼️ Generating image with FULL prompt ({len(final_prompt)} chars): {final_prompt}")
        logger.info(f"🖼️ Prompt breakdown:")
        logger.info(f"   - Article summary: {article_summary[:100]}...")
        logger.info(f"   - Global agent prompt: {global_image_agent_prompt[:100]}...")
        if additional_creative_agent_prompt:
            logger.info(f"   - Custom agent prompt: {additional_creative_agent_prompt[:100]}...")
        if style_components:
            logger.info(f"   - Style components: {', '.join(style_components)}")
        
        # Get API key for image generation
        api_key = get_openai_api_key(current_user=current_user, db=db)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable or configure in Admin Settings > System > Platform Keys."
            )
        
        # Generate image using the combined prompt
        # The generate_image function takes (query, content, api_key) where:
        # - query: used for style matching in Airtable
        # - content: the actual prompt for DALL·E
        # - api_key: OpenAI API key for authentication
        try:
            image_url = generate_image(query=article_content, content=final_prompt, api_key=api_key)
            
            return {
                "status": "success",
                "image_url": image_url,
                "message": image_url
            }
        except Exception as img_error:
            logger.error(f"Error generating image: {img_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate image: {str(img_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_image_machine_content endpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Also support GET for backward compatibility
@content_generation_router.get("/generate_image_machine_content")
async def generate_image_machine_content_get(
    id: str,
    query: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """GET endpoint for image generation (backward compatibility)"""
    try:
        # Import image generation function
        try:
            from tools import generate_image
        except ImportError:
            logger.error("Could not import generate_image from tools")
            raise HTTPException(
                status_code=500,
                detail="Image generation service not available"
            )
        
        # Build prompt from article content (query parameter)
        article_content = query
        article_summary = article_content[:300].strip() if len(article_content) > 300 else article_content.strip()
        final_prompt = f"{article_summary}. Create a relevant, visually appealing image."
        
        logger.info(f"🖼️ Generating image (GET) with prompt: {final_prompt[:200]}...")
        
        # Generate image
        try:
            image_url = generate_image(query=article_content, content=final_prompt)
            
            return {
                "status": "success",
                "image_url": image_url,
                "message": image_url
            }
        except Exception as img_error:
            logger.error(f"Error generating image: {img_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate image: {str(img_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_image_machine_content GET endpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Image Serving Endpoint
@content_generation_router.get("/images/{filename}")
async def serve_image(filename: str):
    """
    Serve images from the uploads/images directory.
    Images are saved here by generate_image function in tools.py
    """
    try:
        import os
        from fastapi.responses import FileResponse
        from pathlib import Path
        
        # Get the directory where content.py is located
        current_dir = Path(__file__).parent.parent.parent
        upload_dir = current_dir / "uploads" / "images"
        file_path = upload_dir / filename
        
        # Security: Validate filename (prevent path traversal)
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Check if file exists
        if not file_path.exists():
            logger.warning(f"Image not found: {file_path}")
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Return the image file
        return FileResponse(
            path=str(file_path),
            media_type="image/png",  # Default to PNG, but could detect from extension
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving image {filename}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to serve image: {str(e)}")
