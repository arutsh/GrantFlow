from typing import Dict, Any, Optional, List, cast
from uuid import UUID

import structlog

from app.db.session import SessionLocal
from app.models.user_cache import UserProfileModel
from app.services.user_client import get_user, get_users_by_ids

logger = structlog.get_logger(__name__)


def get_user_from_cache(user_id: UUID) -> Optional[Dict[str, Any]]:
    session = SessionLocal()
    try:
        profile = (
            session.query(UserProfileModel).filter(UserProfileModel.user_id == user_id).first()
        )

        if not profile:
            logger.debug("cache_miss", user_id=str(user_id))
            return None

        logger.debug("cache_hit", user_id=str(user_id))
        return {
            "id": str(profile.user_id),
            "email": profile.email,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "status": profile.status,
            "customer_id": str(profile.customer_id) if profile.customer_id else None,
            "role": profile.role,
        }
    finally:
        session.close()


def get_user_from_cache_or_fallback(user_id: UUID, token: str) -> Optional[Dict[str, Any]]:
    cached = get_user_from_cache(user_id)
    if cached:
        return cached

    logger.warning("cache_miss_fallback_attempted", user_id=str(user_id))

    try:
        user = get_user(str(user_id), token)

        session = SessionLocal()
        try:
            profile = (
                session.query(UserProfileModel).filter(UserProfileModel.user_id == user_id).first()
            )

            if profile:
                profile.email = cast(str, user.get("email"))
                profile.first_name = user.get("first_name")
                profile.last_name = user.get("last_name")
                profile.status = cast(str, user.get("status"))
                profile.customer_id = (
                    UUID(user.get("customer_id")) if user.get("customer_id") else None
                )
                profile.role = cast(str, user.get("role"))
            else:
                profile = UserProfileModel(
                    user_id=user_id,
                    email=user.get("email"),
                    first_name=user.get("first_name"),
                    last_name=user.get("last_name"),
                    status=user.get("status"),
                    customer_id=(
                        UUID(user.get("customer_id")) if user.get("customer_id") else None
                    ),
                    role=user.get("role"),
                )
                session.add(profile)

            session.commit()
            logger.info("cache_populated_from_fallback", user_id=str(user_id))
        finally:
            session.close()

        return user
    except Exception as e:
        logger.error(
            "fallback_http_failed",
            user_id=str(user_id),
            error=str(e),
        )
        raise


async def get_users_by_ids_cached(ids: List[str], token: str) -> Dict[str, Dict[str, Any]]:
    """Get users from cache, falling back to HTTP for cache misses."""
    if not ids:
        return {}

    session = SessionLocal()
    try:
        user_uuids = [uid if isinstance(uid, UUID) else UUID(uid) for uid in ids]
        profiles = (
            session.query(UserProfileModel).filter(UserProfileModel.user_id.in_(user_uuids)).all()
        )

        cached_map = {
            str(p.user_id): {
                "id": str(p.user_id),
                "email": p.email,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "status": p.status,
                "customer_id": str(p.customer_id) if p.customer_id else None,
                "role": p.role,
            }
            for p in profiles
        }

        cached_ids = {p.user_id for p in profiles}
        missing_ids = [uid for uid in user_uuids if uid not in cached_ids]

        if not missing_ids:
            logger.debug("cache_hit_all_users", count=len(cached_map))
            return cached_map

        logger.warning("cache_miss_partial", missing_count=len(missing_ids), total=len(ids))

        try:
            http_users = await get_users_by_ids([str(uid) for uid in missing_ids], token)

            for user_id, user_data in http_users.items():
                uid = UUID(user_id)
                existing = (
                    session.query(UserProfileModel).filter(UserProfileModel.user_id == uid).first()
                )

                if existing:
                    existing.email = cast(str, user_data.get("email"))
                    existing.first_name = user_data.get("first_name")
                    existing.last_name = user_data.get("last_name")
                    existing.status = cast(str, user_data.get("status"))
                    existing.customer_id = (
                        UUID(user_data.get("customer_id")) if user_data.get("customer_id") else None
                    )
                    existing.role = cast(str, user_data.get("role"))
                else:
                    profile = UserProfileModel(
                        user_id=uid,
                        email=user_data.get("email"),
                        first_name=user_data.get("first_name"),
                        last_name=user_data.get("last_name"),
                        status=user_data.get("status"),
                        customer_id=(
                            UUID(user_data.get("customer_id"))
                            if user_data.get("customer_id")
                            else None
                        ),
                        role=user_data.get("role"),
                    )
                    session.add(profile)

            session.commit()
            logger.info("cache_populated_from_http", count=len(http_users))
            cached_map.update(http_users)
        except Exception as e:
            session.rollback()
            logger.error(
                "batch_fallback_http_failed",
                missing_count=len(missing_ids),
                error=str(e),
            )
            raise

        return cached_map
    finally:
        session.close()
