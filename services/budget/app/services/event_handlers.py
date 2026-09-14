from typing import Dict, Any, cast
from uuid import UUID

import structlog
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.user_cache import UserProfileModel

logger = structlog.get_logger(__name__)

MAX_RETRIES = 3


class EventProcessingError(Exception):
    def __init__(self, message: str, requeue: bool = True):
        super().__init__(message)
        self.requeue = requeue


async def handle_user_event(event_type: str, payload: Dict[str, Any]) -> None:
    if event_type == "user.created":
        await handle_user_created(payload)
    elif event_type == "user.updated":
        await handle_user_updated(payload)
    elif event_type == "user.deleted":
        await handle_user_deleted(payload)
    else:
        logger.warning("unknown_event_type", event_type=event_type)
        raise EventProcessingError(
            f"Unknown event type: {event_type}",
            requeue=False,
        )


async def handle_user_created(payload: Dict[str, Any]) -> None:
    async with AsyncSessionLocal() as session:
        try:
            user_id = UUID(payload.get("user_id"))

            result = await session.execute(
                select(UserProfileModel).where(UserProfileModel.user_id == user_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.warning(
                    "user_created_already_cached",
                    user_id=str(user_id),
                )
                return

            profile = UserProfileModel(
                user_id=user_id,
                email=payload.get("email"),
                first_name=payload.get("first_name"),
                last_name=payload.get("last_name"),
                status=payload.get("status"),
                customer_id=(
                    UUID(payload.get("customer_id")) if payload.get("customer_id") else None
                ),
                role=payload.get("role"),
            )
            session.add(profile)
            await session.commit()
            logger.info("user_cache_created", user_id=str(user_id))
        except Exception as e:
            await session.rollback()
            logger.error(
                "user_created_handler_failed",
                error=str(e),
                payload=payload,
            )
            raise EventProcessingError(str(e), requeue=True)


async def handle_user_updated(payload: Dict[str, Any]) -> None:
    async with AsyncSessionLocal() as session:
        try:
            user_id = UUID(payload.get("user_id"))

            result = await session.execute(
                select(UserProfileModel).where(UserProfileModel.user_id == user_id)
            )
            profile = result.scalar_one_or_none()

            if not profile:
                logger.warning(
                    "user_updated_not_in_cache",
                    user_id=str(user_id),
                )
                profile = UserProfileModel(
                    user_id=user_id,
                    email=payload.get("email"),
                    first_name=payload.get("first_name"),
                    last_name=payload.get("last_name"),
                    status=payload.get("status"),
                    customer_id=(
                        UUID(payload.get("customer_id")) if payload.get("customer_id") else None
                    ),
                    role=payload.get("role"),
                )
                session.add(profile)
            else:
                profile.email = cast(str, payload.get("email"))
                profile.first_name = payload.get("first_name")
                profile.last_name = payload.get("last_name")
                profile.status = cast(str, payload.get("status"))
                profile.customer_id = (
                    UUID(payload.get("customer_id")) if payload.get("customer_id") else None
                )
                profile.role = cast(str, payload.get("role"))

            await session.commit()
            logger.info("user_cache_updated", user_id=str(user_id))
        except Exception as e:
            await session.rollback()
            logger.error(
                "user_updated_handler_failed",
                error=str(e),
                payload=payload,
            )
            raise EventProcessingError(str(e), requeue=True)


async def handle_user_deleted(payload: Dict[str, Any]) -> None:
    async with AsyncSessionLocal() as session:
        try:
            user_id = UUID(payload.get("user_id"))

            result = await session.execute(
                select(UserProfileModel).where(UserProfileModel.user_id == user_id)
            )
            profile = result.scalar_one_or_none()

            if profile:
                await session.delete(profile)
                await session.commit()
                logger.info("user_cache_deleted", user_id=str(user_id))
            else:
                logger.warning(
                    "user_deleted_not_in_cache",
                    user_id=str(user_id),
                )
        except Exception as e:
            await session.rollback()
            logger.error(
                "user_deleted_handler_failed",
                error=str(e),
                payload=payload,
            )
            raise EventProcessingError(str(e), requeue=True)
