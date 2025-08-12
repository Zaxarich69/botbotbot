import os
import logging
from typing import Optional

import pytz
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from services.lottery import draw_lottery

log = logging.getLogger(__name__)


def _parse_int_env(name: str, default: int, min_value: int, max_value: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {name}={raw!r}: must be an integer")
    if not (min_value <= value <= max_value):
        raise ValueError(f"Invalid {name}={value}: must be in [{min_value}, {max_value}]")
    return value


def _get_timezone(env_name: str, default_tz: str) -> pytz.BaseTzInfo:
    # Prefer specific env (e.g., DRAW_TIMEZONE), then generic TIMEZONE, then default
    tz_name = os.getenv(env_name) or os.getenv("TIMEZONE", default_tz)
    try:
        return pytz.timezone(tz_name)
    except Exception as e:
        raise ValueError(f"Invalid {env_name}={tz_name!r}: {e}") from e


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    # Timezone (default VET = America/Caracas; no DST)
    timezone = _get_timezone("DRAW_TIMEZONE", "America/Caracas")

    # Read and validate schedule configuration (support new and legacy envs)
    day = os.getenv("DRAW_CRON_DAY_OF_WEEK") or os.getenv("DRAW_DAY_OF_WEEK", "thu")
    hour = _parse_int_env("DRAW_CRON_HOUR", _parse_int_env("DRAW_HOUR", 20, 0, 23), 0, 23)
    minute = _parse_int_env("DRAW_CRON_MINUTE", _parse_int_env("DRAW_MINUTE", 0, 0, 59), 0, 59)

    # Build a CronTrigger early to validate day_of_week
    try:
        trigger = CronTrigger(day_of_week=day, hour=hour, minute=minute, timezone=timezone)
    except Exception as e:
        raise ValueError(f"Invalid cron configuration (day={day!r}, hour={hour}, minute={minute}): {e}") from e

    scheduler = AsyncIOScheduler(timezone=timezone)

    # Use a fixed job id to avoid duplicates across restarts; replace if exists
    job_id = "weekly_lottery_draw"
    try:
        scheduler.add_job(
            func=draw_lottery,
            trigger=trigger,
            args=[bot],
            id=job_id,
            replace_existing=True,
            coalesce=True,              # collapse multiple pending runs into one
            misfire_grace_time=300,     # 5 minutes grace period
            max_instances=1,            # prevent overlapping draws
        )
    except Exception as e:
        log.error(f"Failed to add scheduler job: {e}")
        raise

    scheduler.start()

    # Log the effective schedule and timezone clearly
    log.info(
        "Scheduler started. Draw is set for cron(day_of_week=%s, hour=%02d, minute=%02d) in timezone %s.",
        day, hour, minute, timezone.zone
    )

    return scheduler
