#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import requests


DEFAULT_ENDPOINTS = [
    {"name": "dashboard_summary", "path": "/dashboard/summary"},
    {"name": "leads", "path": "/leads"},
    {"name": "customers", "path": "/customers"},
    {"name": "billing_records", "path": "/billing-records"},
    {"name": "billing_records_summary", "path": "/billing-records/summary"},
    {"name": "dashboard_system_todos", "path": "/dashboard/system-todos"},
]


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = ratio * (len(ordered) - 1)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def login(base_url: str, username: str, password: str) -> str:
    response = requests.post(
        f"{base_url}/auth/login",
        json={"username": username, "password": password},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def sample_endpoint(session: requests.Session, url: str, iterations: int) -> dict:
    durations: list[float] = []
    failures = 0
    status_codes: dict[str, int] = {}

    for _ in range(iterations):
        started = time.perf_counter()
        try:
            response = session.get(url, timeout=15)
            elapsed_ms = (time.perf_counter() - started) * 1000
            durations.append(elapsed_ms)
            status_codes[str(response.status_code)] = status_codes.get(str(response.status_code), 0) + 1
            if response.status_code >= 400:
                failures += 1
        except requests.RequestException:
            elapsed_ms = (time.perf_counter() - started) * 1000
            durations.append(elapsed_ms)
            failures += 1
            status_codes["EXC"] = status_codes.get("EXC", 0) + 1

    return {
        "count": iterations,
        "p50_ms": round(percentile(durations, 0.50), 2),
        "p95_ms": round(percentile(durations, 0.95), 2),
        "max_ms": round(max(durations) if durations else 0.0, 2),
        "mean_ms": round(statistics.mean(durations) if durations else 0.0, 2),
        "failures": failures,
        "status_codes": status_codes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sample API response times for dev trial performance checks.")
    parser.add_argument("--base-url", default="http://127.0.0.1:32000/api/v1")
    parser.add_argument("--username", default="boss")
    parser.add_argument("--password", default="Daizhang#2026!")
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = login(args.base_url, args.username, args.password)

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

    started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    results = {}
    for endpoint in DEFAULT_ENDPOINTS:
        results[endpoint["name"]] = {
            "path": endpoint["path"],
            **sample_endpoint(session, f"{args.base_url}{endpoint['path']}", args.iterations),
        }

    payload = {
        "base_url": args.base_url,
        "username": args.username,
        "iterations": args.iterations,
        "started_at": started_at,
        "endpoints": results,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"run_api_perf_sample failed: {exc}", file=sys.stderr)
        raise
