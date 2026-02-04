import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import PlainTextResponse

from brief import run_daily_brief

logger = logging.getLogger(__name__)

app = FastAPI(title="Daily Brief Agent")


def _bool_env(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def _require_token(x_dailybrief_token: Optional[str] = Header(default=None, alias="X-Dailybrief-Token")) -> None:
    expected = os.getenv("DAILYBRIEF_ACCESS_TOKEN")
    if not expected:
        return
    if x_dailybrief_token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _get_schedule() -> tuple[ZoneInfo, int, int]:
    tz_name = os.getenv("DAILYBRIEF_TZ", "America/Chicago")
    hhmm = os.getenv("DAILYBRIEF_RUN_HHMM", "07:00")

    try:
        tz = ZoneInfo(tz_name)
    except Exception as e:
        raise RuntimeError(f"Invalid DAILYBRIEF_TZ={tz_name}: {e}") from e

    try:
        hour_s, minute_s = hhmm.split(":")
        hour = int(hour_s)
        minute = int(minute_s)
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError("hour/minute out of range")
    except Exception as e:
        raise RuntimeError(f"Invalid DAILYBRIEF_RUN_HHMM={hhmm}: {e}") from e

    return tz, hour, minute


def _next_run_after(now: datetime, hour: int, minute: int) -> datetime:
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


async def _scheduler_loop() -> None:
    tz, hour, minute = _get_schedule()
    logger.info("Scheduler enabled: tz=%s run=%02d:%02d", tz.key, hour, minute)

    while True:
        now = datetime.now(tz)
        next_run = _next_run_after(now, hour, minute)
        sleep_s = max(1, int((next_run - now).total_seconds()))

        logger.info("Next scheduled run at %s (%ds)", next_run.isoformat(), sleep_s)
        await asyncio.sleep(sleep_s)

        try:
            await asyncio.to_thread(run_daily_brief)
            logger.info("Scheduled run complete")
        except Exception:
            logger.exception("Scheduled run failed")


@app.on_event("startup")
async def _on_startup() -> None:
    if _bool_env("DAILYBRIEF_RUN_ON_STARTUP", default=True):
        try:
            await asyncio.to_thread(run_daily_brief)
            logger.info("Startup run complete")
        except Exception:
            logger.exception("Startup run failed")

    if _bool_env("DAILYBRIEF_SCHEDULE_ENABLED", default=False):
        asyncio.create_task(_scheduler_loop())


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/run")
async def run_now(x_dailybrief_token: Optional[str] = Header(default=None, alias="X-Dailybrief-Token")) -> dict:
    _require_token(x_dailybrief_token)
    result = await asyncio.to_thread(run_daily_brief)
    return result


@app.get("/latest", response_class=PlainTextResponse)
def latest_markdown(x_dailybrief_token: Optional[str] = Header(default=None, alias="X-Dailybrief-Token")) -> str:
    _require_token(x_dailybrief_token)
    output_dir = Path(os.getenv("DAILYBRIEF_OUTPUT_DIR", "./output"))
    latest_path = output_dir / "latest.md"
    if not latest_path.exists():
        raise HTTPException(status_code=404, detail="No latest brief found")
    return latest_path.read_text(encoding="utf-8")

