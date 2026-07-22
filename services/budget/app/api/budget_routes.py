# /services/budget/app/api/budget_routes.py
import json
import logging
import traceback
import urllib.parse

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from uuid import uuid4, UUID  # noqa: F401

from app.core.config import settings
from app.db.session import SessionLocal
from app.schemas.budget_schema import (
    BudgetCreate,
    BudgetUpdate,
    BudgetWithLines,
    FundedBudgetsSummary,
    GranteeSummary,
    FundedBudgetListItem,
)
from app.schemas.budget_line_schema import BudgetLine
from app.schemas.with_lines_schema import CreateBudgetWithLinesRequest
from app.services.budget_line_services import get_viewable_budget_lines_service
from app.services.budget_services import (
    create_budget_service,
    create_budget_with_lines_service,
    get_viewable_budget_service,
    update_budget_service,
    list_budget_service,
    delete_budget_service,
    get_funded_budgets_summary_service,
    get_funded_grantees_service,
    get_funded_budgets_service,
)
from app.services.customer_client import require_donor
from shared.security.dependencies import get_validated_user  # noqa: F401

logger = logging.getLogger(__name__)


class AiCreateBudgetStreamRequest(BaseModel):
    text: str


router = APIRouter(prefix="/budgets", tags=["Public Budgets"])
private_router = APIRouter(prefix="/budgets", tags=["Private Budgets"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
async def create_budget_endpoint(
    budget: BudgetCreate,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    return await create_budget_service(budget, valid_user, db, include_user_datails=True)


@router.get("/funded/summary", response_model=FundedBudgetsSummary)
async def get_funded_budgets_summary_endpoint(
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    require_donor(valid_user)
    return get_funded_budgets_summary_service(valid_user["customer_id"], db)


@router.get("/funded/grantees", response_model=list[GranteeSummary])
async def get_funded_grantees_endpoint(
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    require_donor(valid_user)
    return await get_funded_grantees_service(valid_user["customer_id"], valid_user, db)


@router.get("/funded/", response_model=list[FundedBudgetListItem])
async def get_funded_budgets_endpoint(
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    require_donor(valid_user)
    return await get_funded_budgets_service(valid_user["customer_id"], valid_user, db)


@router.get("/{budget_id}", response_model=BudgetWithLines)
async def get_budget_endpoint(
    budget_id: UUID,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    budget = await get_viewable_budget_service(budget_id, valid_user, db, include_user_details=True)
    if budget:
        budget_lines = get_viewable_budget_lines_service(
            db=db, valid_user=valid_user, budget_id=budget_id
        )
        budget["lines"] = [BudgetLine.model_validate(line) for line in budget_lines]
    return budget


@router.patch("/{budget_id}", response_model=BudgetUpdate)
async def update_budget_endpoint(
    budget_id: UUID,
    budget: BudgetUpdate,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    updated_budget = await update_budget_service(
        budget_id=budget_id, budget=budget, valid_user=valid_user, db=db
    )
    if not updated_budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return updated_budget


@router.get("/")
async def get_all_budgets_endpoint(
    db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):

    return await list_budget_service(db=db, valid_user=valid_user, include_user_details=True)


@router.post("/with-lines")
async def create_budget_with_lines_endpoint(
    request: CreateBudgetWithLinesRequest,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    return await create_budget_with_lines_service(request, valid_user, db)


@router.post("/ai/stream")
async def ai_create_budget_stream_endpoint(
    request: AiCreateBudgetStreamRequest,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    """
    SSE proxy: calls AI service to parse text, creates the budget in DB,
    then streams back a 'created' event with the new budget_id.
    """
    ai_url = f"{settings.ai_service_url}/ai/parse-budget/stream"
    token = valid_user.get("token", "")
    encoded_text = urllib.parse.quote(request.text)

    async def generate():
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                async with client.stream(
                    "GET",
                    f"{ai_url}?text={encoded_text}",
                    headers={"Authorization": f"Bearer {token}"},
                ) as response:
                    buffer = ""
                    current_event = ""

                    async for chunk in response.aiter_text():
                        buffer += chunk
                        lines = buffer.split("\n")
                        buffer = lines.pop()

                        for line in lines:
                            if line.startswith("event: "):
                                current_event = line[7:].strip()
                            elif line.startswith("data: "):
                                data = line[6:]
                                if current_event == "progress":
                                    yield f"event: progress\ndata: {data}\n\n"
                                elif current_event == "done":
                                    progress = (
                                        "event: progress\ndata: "
                                        '{"status": "Creating budget..."}\n\n'
                                    )
                                    yield progress
                                    try:
                                        parsed = json.loads(data)
                                        created = await create_budget_with_lines_service(
                                            CreateBudgetWithLinesRequest(
                                                budget_name=parsed["budget_name"],
                                                external_funder_name=parsed.get(
                                                    "external_funder_name"
                                                )
                                                or "",
                                                duration_months=parsed.get("duration_months"),
                                                lines=parsed.get("lines", []),
                                            ),
                                            valid_user,
                                            db,
                                        )
                                        budget_id = str(created["id"])
                                        yield (
                                            f"event: created\n"
                                            f'data: {{"budget_id": "{budget_id}"}}\n\n'
                                        )
                                    except Exception as exc:
                                        tb = traceback.format_exc()
                                        logger.error(
                                            "ai/stream budget creation failed: %s\n%s",
                                            exc,
                                            tb,
                                        )
                                        err_msg = str(exc).replace('"', "'")[:200]
                                        yield (
                                            "event: error\n"
                                            'data: {"message": "Failed to create budget",'
                                            f' "detail": "{err_msg}"}}\n\n'
                                        )
                                elif current_event in ("error", "unavailable"):
                                    yield f"event: {current_event}\ndata: {data}\n\n"
                                current_event = ""
        except Exception:
            yield "event: error\ndata: Connection to AI service failed\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete("/{budget_id}")
async def delete_budget_endpoint(
    budget_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    return {
        "success": await delete_budget_service(budget_id=budget_id, valid_user=valid_user, db=db)
    }
