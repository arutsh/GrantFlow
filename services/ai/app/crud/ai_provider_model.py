from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_provider_model import AIProviderModel


async def exists_for_provider(provider_id: str, name: str, db: AsyncSession) -> bool:
    result = await db.execute(
        select(AIProviderModel.id).where(
            AIProviderModel.provider_id == provider_id,
            AIProviderModel.name == name,
            AIProviderModel.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none() is not None
