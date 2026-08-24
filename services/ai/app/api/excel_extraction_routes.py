"""Structured Excel-line extraction — budget-excel-import spec.

BYOK-preferred, GrantFlow-funded cheap-model fallback when no provider key
is configured, so import quality doesn't depend on the organization having
set up AI (a deliberate, scoped carve-out from the platform's BYOK-only
policy — see budget-export-from-excel design.md Decision 5). Only the
GrantFlow-funded path is rate-limited here; a BYOK call is bounded by the
organization's own provider account.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic_ai.exceptions import AgentRunError

from app.core.config import settings
from app.core.logging import get_logger
from app.services.excel_extraction_service import run_excel_extraction
from app.services.provider import ResolvedModel, get_resolved_model, resolve_platform_funded_model
from app.services.rate_limiter import enforce_rate_limit
from app.utils.security import get_validated_user, resolve_customer_id
from shared.ai_client.schemas import ExcelExtractionRequest, ExcelExtractionResult

logger = get_logger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Excel Extraction"])


@router.post("/extract-budget-excel", response_model=ExcelExtractionResult)
async def extract_budget_excel(
    body: ExcelExtractionRequest,
    valid_user=Depends(get_validated_user),
    resolved: ResolvedModel | None = Depends(get_resolved_model),
):
    customer_id = resolve_customer_id(valid_user)
    user_id = str(valid_user["user_id"])

    funding_source = "byok"
    if resolved is None:
        resolved = resolve_platform_funded_model()
        if resolved is None:
            raise HTTPException(status_code=503, detail={"code": "no_provider"})
        funding_source = "platform"
        await enforce_rate_limit(
            customer_id,
            limit=settings.AI_EXCEL_IMPORT_PLATFORM_RATE_LIMIT_PER_HOUR,
            scope="excel-import-platform",
        )

    try:
        return await run_excel_extraction(
            rows=body.rows,
            resolved=resolved,
            funding_source=funding_source,
            customer_id=customer_id,
            user_id=user_id,
        )
    except AgentRunError as exc:
        logger.error("excel_extraction_model_error", customer_id=customer_id, error=str(exc))
        raise HTTPException(status_code=502, detail={"code": "model_error"}) from exc
    except Exception as exc:
        logger.error("excel_extraction_failed", customer_id=customer_id, error=str(exc))
        raise HTTPException(status_code=502, detail={"code": "extraction_failed"}) from exc
