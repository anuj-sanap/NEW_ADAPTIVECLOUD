"""
backend/app/services/scheduler.py
Background scheduling service for periodic predictive maintenance,
threat forecasting, and empirical model accuracy verification (backfill).
Runs asynchronously every 60 seconds during FastAPI application lifecycle.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.host import Host
from app.services.maintenance import backfill_observed_outcomes, evaluate_predictive_maintenance
from app.services.threat_prediction import generate_threat_forecasts

logger = get_logger("scheduler")


class TelemetryScheduler:
    """Manages periodic execution of maintenance forecasting and threat projections."""

    def __init__(self, interval_seconds: int = 60) -> None:
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("AdaptiveCloud telemetry scheduler started (interval: %ds)", self.interval_seconds)

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("AdaptiveCloud telemetry scheduler stopped")

    async def run_once(self) -> dict[str, Any]:
        """
        Executes one full cycle across all registered hosts.
        Returns execution statistics for testing and on-demand triggers.
        """
        hosts_evaluated = 0
        backfilled = 0
        errors = 0

        async with AsyncSessionLocal() as db:
            try:
                stmt = select(Host)
                res = await db.execute(stmt)
                hosts = res.scalars().all()

                for host in hosts:
                    try:
                        # 1. Predictive maintenance evaluation
                        await evaluate_predictive_maintenance(db, host.id)
                        # 2. Threat forecasting evaluation (15m horizon)
                        await generate_threat_forecasts(db, host.id, horizon_min=15)
                        hosts_evaluated += 1
                    except Exception as e:
                        errors += 1
                        logger.warning("Error evaluating predictions for host %s: %s", host.id, e)

                # 3. Backfill outcomes where horizon has arrived
                try:
                    backfilled = await backfill_observed_outcomes(db)
                except Exception as e:
                    logger.warning("Error during prediction outcome backfill: %s", e)

            except Exception as e:
                logger.error("Database error during scheduler execution cycle: %s", e)

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "hosts_evaluated": hosts_evaluated,
            "backfilled_predictions": backfilled,
            "errors": errors,
        }

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self.interval_seconds)
                if not self._running:
                    break
                await self.run_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Unexpected error in telemetry scheduler loop: %s", e)


telemetry_scheduler = TelemetryScheduler(interval_seconds=60)
