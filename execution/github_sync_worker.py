"""Long-running entrypoint for the github-sync container.

Runs three cadences from one loop:
  - Every SYNC_INTERVAL_SECONDS (default 5): sync_active_tasks_once — a fast,
    cheap recheck of only the Tasks currently In-Progress/Testing.
  - Every DISCOVERY_INTERVAL_SECONDS (default 60): the existing full sync_once —
    discovers brand-new issues and reconciles everything else.
  - Every PLAN_SYNC_INTERVAL_SECONDS (default 15): sync_plan_once — refreshes the live
    PR/CI/review state of the active implementation plans' issues (plan graph colors).

Each cycle's exceptions are isolated so one bad repo/cycle never kills the worker.
The GitHub rate-limit budget is checked only at the slow (discovery) cadence; if
it's low, all cadences are skipped until the next scheduled discovery check.
"""

import logging
import os
import time

from execution.db_client import get_session
from execution.github_sync import get_rate_limit, sync_active_tasks_once, sync_once
from execution.plan_sync import sync_plan_once

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("github_sync_worker")

RATE_LIMIT_SAFETY_THRESHOLD = 50


def run():
    fast_interval = int(os.environ.get("SYNC_INTERVAL_SECONDS", "5"))
    discovery_interval = int(os.environ.get("DISCOVERY_INTERVAL_SECONDS", "60"))
    plan_interval = int(os.environ.get("PLAN_SYNC_INTERVAL_SECONDS", "15"))
    last_polled = {}
    budget_healthy = True
    next_discovery_at = time.monotonic()
    next_plan_at = time.monotonic()

    logger.info(
        "github-sync worker starting, fast_interval=%ss discovery_interval=%ss plan_interval=%ss",
        fast_interval, discovery_interval, plan_interval,
    )

    while True:
        now = time.monotonic()

        if now >= next_discovery_at:
            next_discovery_at = now + discovery_interval
            try:
                remaining = get_rate_limit()["remaining"]
                budget_healthy = remaining >= RATE_LIMIT_SAFETY_THRESHOLD
                if not budget_healthy:
                    logger.warning("GitHub rate limit low (remaining=%s); pausing until next discovery check", remaining)
            except Exception:
                logger.exception("Failed to check rate limit; assuming budget is unhealthy this round")
                budget_healthy = False

            if budget_healthy:
                session = get_session()
                try:
                    summary = sync_once(session, last_polled)
                    if summary["created"] or summary["updated"] or summary["errors"]:
                        logger.info(
                            "Discovery cycle complete: created=%s updated=%s errors=%s",
                            summary["created"], summary["updated"], summary["errors"],
                        )
                except Exception:
                    logger.exception("Unhandled error during discovery cycle; will retry next discovery tick")
                finally:
                    session.close()

        if budget_healthy:
            session = get_session()
            try:
                summary = sync_active_tasks_once(session)
                if summary["updated"] or summary["errors"]:
                    logger.info(
                        "Active-task cycle complete: updated=%s errors=%s",
                        summary["updated"], summary["errors"],
                    )
            except Exception:
                logger.exception("Unhandled error during active-task cycle; will retry next cycle")
            finally:
                session.close()

        if budget_healthy and time.monotonic() >= next_plan_at:
            next_plan_at = time.monotonic() + plan_interval
            session = get_session()
            try:
                summary = sync_plan_once(session)
                if summary["updated"] or summary["errors"]:
                    logger.info(
                        "Plan cycle complete: updated=%s transitions=%s errors=%s",
                        summary["updated"], summary["transitions"], summary["errors"],
                    )
            except Exception:
                logger.exception("Unhandled error during plan cycle; will retry next plan tick")
            finally:
                session.close()

        time.sleep(fast_interval)


if __name__ == "__main__":
    run()
