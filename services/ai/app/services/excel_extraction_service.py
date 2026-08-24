import json
import time

from jinja2 import Template
from pydantic_ai import Agent

from app.core.logging import get_logger
from app.services.audit import write_audit_log
from app.services.prompt_loader import load_prompt
from app.services.provider import ResolvedModel
from shared.ai_client.schemas import ExcelExtractionResult

logger = get_logger(__name__)


async def run_excel_extraction(
    *,
    rows: list[list[str | None]],
    resolved: ResolvedModel,
    funding_source: str,
    customer_id: str,
    user_id: str,
) -> ExcelExtractionResult:
    """Structured-output extraction of budget lines from a cleaned sheet grid.

    Mirrors parse_service.py's Agent+audit-log pattern, but is a single
    request/response call (no SSE) and threads `funding_source` (BYOK vs
    GrantFlow-funded) through to the audit log — see budget-export-from-excel
    design.md Decision 5.
    """
    loaded_prompt = await load_prompt("excel_budget_extraction")
    input_text = json.dumps(rows)
    user_message = Template(loaded_prompt.user_template).render(rows_json=input_text)

    start = time.monotonic()
    success = True
    error_message = None
    output_json = None
    input_tokens = 0
    output_tokens = 0

    try:
        agent: Agent[None, ExcelExtractionResult] = Agent(
            resolved.model,
            output_type=ExcelExtractionResult,
            system_prompt=loaded_prompt.system_prompt,
        )
        result = await agent.run(user_message)

        usage = result.usage
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0

        extraction: ExcelExtractionResult = result.output
        output_json = extraction.model_dump()
        return extraction
    except Exception as exc:
        success = False
        error_message = str(exc)
        logger.error(
            "ai_excel_extraction_error",
            error=error_message,
            customer_id=customer_id,
            user_id=user_id,
        )
        raise
    finally:
        duration_ms = int((time.monotonic() - start) * 1000)
        try:
            await write_audit_log(
                customer_id=customer_id,
                user_id=user_id,
                prompt_version=loaded_prompt.version,
                input_text=input_text,
                output_json=output_json,
                provider=resolved.provider_name,
                model=resolved.model_name,
                funding_source=funding_source,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                success=success,
                error_message=error_message,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            logger.error(
                "audit_log_write_failed",
                error=str(exc),
                customer_id=customer_id,
                user_id=user_id,
            )
