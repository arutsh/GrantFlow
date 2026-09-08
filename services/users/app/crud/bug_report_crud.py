from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bug_report import BugReportModel


async def create_bug_report(
    session: AsyncSession,
    bug_report_id: UUID,
    user_id: UUID,
    description: str,
    page_path: str,
    user_agent: str,
    client_timestamp: datetime,
    screenshot_storage_key: str | None = None,
) -> BugReportModel:
    bug_report = BugReportModel(
        id=bug_report_id,
        user_id=user_id,
        description=description,
        page_path=page_path,
        user_agent=user_agent,
        client_timestamp=client_timestamp,
        screenshot_storage_key=screenshot_storage_key,
    )
    session.add(bug_report)
    await session.commit()
    return bug_report
