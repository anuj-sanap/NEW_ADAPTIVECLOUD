"""
scripts/load_test.py
Asynchronous Telemetry Ingestion Load Tester for AdaptiveCloud.
Simulates high-throughput agent traffic (system metrics & network flow telemetry)
to benchmark pipeline throughput, queuing latency, and verify non-blocking performance
under realistic loads for free-tier GCP e2-medium / local container deployments.

Supports:
- In-process ASGI testing (zero-setup, using async SQLite memory engine)
- Live HTTP/HTTPS testing (against http://localhost:8000 or production URL)
- Latency percentiles: p50, p90, p95, p99, min, max, throughput (req/sec)
"""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
import random
import sys
import time
from datetime import UTC, datetime

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import httpx
from app.core.config import get_settings
from ml.features.feature_map import CANONICAL_FEATURES

settings = get_settings()


def print_banner():
    print("""
========================================================================
   ADAPTIVECLOUD - HIGH-THROUGHPUT TELEMETRY INGESTION BENCHMARK
========================================================================
 Benchmarking:
   - Concurrent Agent Telemetry Streams (Metrics & Flow Telemetry)
   - Real-time Pipeline Throughput & Latency Distribution (p50, p95, p99)
   - Database Write Stability & Non-Blocking Async Ingestion
========================================================================
""")


async def run_load_test(
    base_url: str = "http://localhost:8000",
    in_process: bool = True,
    duration_sec: int = 10,
    target_concurrency: int = 20,
    rps_limit: int = 100,
):
    print(f"[*] Mode: {'In-Process ASGI Driver' if in_process else 'Live Network HTTP/HTTPS'}")
    if in_process and target_concurrency > 1:
        # SQLite in-memory engine is single-threaded; clamp concurrency for in-process mode
        target_concurrency = 1
    print(f"[*] Target Concurrency: {target_concurrency} concurrent workers")
    print(f"[*] Duration: {duration_sec} seconds")
    print(f"[*] Target Rate Cap: ~{rps_limit} requests/sec\n")

    app = None
    if in_process:
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from sqlalchemy.pool import StaticPool
        from app.db.base import Base
        from app.db.session import get_db
        from app.main import app as fastapi_app
        import app.models  # ensure models are imported

        mem_engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with mem_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        test_session_maker = async_sessionmaker(
            bind=mem_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        async def _override_get_db():
            async with test_session_maker() as session:
                yield session

        fastapi_app.dependency_overrides[get_db] = _override_get_db
        app = fastapi_app

    transport = httpx.ASGITransport(app=app) if in_process else None
    client_kwargs = {"base_url": base_url, "timeout": httpx.Timeout(30.0)}
    if transport:
        client_kwargs["transport"] = transport

    async with httpx.AsyncClient(**client_kwargs) as client:
        # Pre-flight: Register benchmark test host
        agent_api_key = settings.AGENT_API_KEY
        agent_headers = {"X-API-Key": agent_api_key, "Content-Type": "application/json"}

        reg_res = await client.post(
            "/api/v1/agents/register",
            json={
                "hostname": "loadtest-worker-node-01",
                "os_version": "Windows Server 2022 Datacenter",
                "agent_platform": "windows",
                "ip_address": "100.64.0.50",
            },
            headers=agent_headers,
        )
        if reg_res.status_code != 200:
            print(f"[!] Worker registration failed: {reg_res.status_code} {reg_res.text}")
            return False

        latencies_ms: list[float] = []
        errors: list[str] = []
        start_time = time.perf_counter()
        stop_event = asyncio.Event()

        # Pre-build canonical flow features template
        base_features = {f: 10.0 for f in CANONICAL_FEATURES}

        async def worker():
            nonlocal latencies_ms, errors
            while not stop_event.is_set():
                endpoint_choice = random.random()
                req_t0 = time.perf_counter()
                try:
                    now_iso = datetime.now(UTC).isoformat()
                    if endpoint_choice < 0.5:
                        # Ingest Metrics
                        payload = {
                            "ts": now_iso,
                            "cpu": round(random.uniform(10.0, 95.0), 2),
                            "mem": round(random.uniform(30.0, 85.0), 2),
                            "disk": 45.0,
                            "net_in": round(random.uniform(100.0, 50000.0), 1),
                            "net_out": round(random.uniform(100.0, 20000.0), 1),
                            "load": 0.6,
                            "proc_count": 82,
                            "conn_count": 18,
                            "extra": {"load_test": True},
                        }
                        res = await client.post("/api/v1/agents/metrics", json=payload, headers=agent_headers)
                    else:
                        # Ingest Flows
                        f_copy = base_features.copy()
                        f_copy["flow_pkts_s"] = random.uniform(5.0, 5000.0)
                        f_copy["flow_bytes_s"] = random.uniform(500.0, 1000000.0)
                        payload = {"ts": now_iso, "features": f_copy}
                        res = await client.post("/api/v1/agents/flows", json=payload, headers=agent_headers)

                    req_latency = (time.perf_counter() - req_t0) * 1000.0
                    if res.status_code in (200, 201, 202):
                        latencies_ms.append(req_latency)
                    else:
                        errors.append(f"HTTP {res.status_code}: {res.text[:80]}")
                except Exception as e:
                    errors.append(str(e))

                # Yield control to regulate rate
                await asyncio.sleep(1.0 / (rps_limit / target_concurrency))

        print("[*] Spawning load generation coroutines...")
        tasks = [asyncio.create_task(worker()) for _ in range(target_concurrency)]

        # Let the test run for duration_sec
        await asyncio.sleep(duration_sec)
        stop_event.set()
        await asyncio.gather(*tasks, return_exceptions=True)

        total_elapsed = time.perf_counter() - start_time
        total_requests = len(latencies_ms) + len(errors)
        success_count = len(latencies_ms)
        success_rate = (success_count / total_requests * 100.0) if total_requests > 0 else 0.0
        rps_achieved = total_requests / total_elapsed if total_elapsed > 0 else 0.0

        latencies_ms.sort()
        p50 = latencies_ms[int(len(latencies_ms) * 0.50)] if latencies_ms else 0.0
        p90 = latencies_ms[int(len(latencies_ms) * 0.90)] if latencies_ms else 0.0
        p95 = latencies_ms[int(len(latencies_ms) * 0.95)] if latencies_ms else 0.0
        p99 = latencies_ms[int(len(latencies_ms) * 0.99)] if latencies_ms else 0.0
        min_lat = latencies_ms[0] if latencies_ms else 0.0
        max_lat = latencies_ms[-1] if latencies_ms else 0.0
        avg_lat = (sum(latencies_ms) / len(latencies_ms)) if latencies_ms else 0.0

        print("\n" + "=" * 65)
        print("          LOAD TEST & THROUGHPUT BENCHMARK RESULTS")
        print("=" * 65)
        print(f"  Duration:                  {total_elapsed:.2f} s")
        print(f"  Total Ingestion Requests:  {total_requests}")
        print(f"  Successful Requests:       {success_count}")
        print(f"  Failed Requests:           {len(errors)}")
        print(f"  Success Rate:              {success_rate:.2f} %")
        print(f"  Sustained Throughput:      {rps_achieved:.1f} req/sec")
        print("-" * 65)
        print(f"  Latency Min:               {min_lat:.2f} ms")
        print(f"  Latency Avg:               {avg_lat:.2f} ms")
        print(f"  Latency p50 (Median):      {p50:.2f} ms")
        print(f"  Latency p90:               {p90:.2f} ms")
        print(f"  Latency p95:               {p95:.2f} ms")
        print(f"  Latency p99:               {p99:.2f} ms")
        print(f"  Latency Max:               {max_lat:.2f} ms")
        print("=" * 65)

        if errors:
            print(f"\n[!] Top Errors Encountered ({len(errors)} total):")
            for err in set(errors[:5]):
                print(f"    - {err}")

        passed = success_rate >= 99.0 and p95 < 250.0
        if passed:
            print("\n>>> BENCHMARK PASSED: System achieved >99% success under target load! [GREEN]\n")
        else:
            print(f"\n>>> BENCHMARK FAILED: Check latency ({p95:.1f}ms) or error rate ({100-success_rate:.1f}%).\n")
        return passed


def main():
    parser = argparse.ArgumentParser(description="AdaptiveCloud Telemetry Ingestion Load Tester")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Base URL of backend API")
    parser.add_argument("--live", action="store_true", help="Run against live running HTTP/HTTPS server")
    parser.add_argument("--duration", type=int, default=3, help="Test duration in seconds (default: 3)")
    parser.add_argument("--concurrency", type=int, default=2, help="Number of concurrent workers (default: 2)")
    parser.add_argument("--rps", type=int, default=50, help="Target requests per second (default: 50)")
    args = parser.parse_args()

    print_banner()
    success = asyncio.run(
        run_load_test(
            base_url=args.api_url,
            in_process=not args.live,
            duration_sec=args.duration,
            target_concurrency=args.concurrency,
            rps_limit=args.rps,
        )
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
