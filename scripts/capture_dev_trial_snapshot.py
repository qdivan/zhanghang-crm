#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from urllib import error, request


def http_json(url: str, method: str = "GET", headers: dict[str, str] | None = None, payload: dict | None = None) -> dict | list:
    data = None
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers=req_headers, method=method)
    with request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def build_report(base_api: str, username: str, password: str) -> str:
    login = http_json(
        f"{base_api}/auth/login",
        method="POST",
        payload={"username": username, "password": password},
    )
    token = login["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    leads = http_json(f"{base_api}/leads", headers=auth)
    customers = http_json(f"{base_api}/customers", headers=auth)
    billings = http_json(f"{base_api}/billing-records", headers=auth)
    billing_summary = http_json(f"{base_api}/billing-records/summary", headers=auth)
    library_items = http_json(f"{base_api}/common-library-items", headers=auth)
    dashboard = http_json(f"{base_api}/dashboard/summary", headers=auth)
    system_todos = http_json(f"{base_api}/dashboard/system-todos", headers=auth)
    users = http_json(f"{base_api}/users", headers=auth)
    address_resources = http_json(f"{base_api}/address-resources", headers=auth)

    lead_status: dict[str, int] = {}
    for item in leads:
        lead_status[item["status"]] = lead_status.get(item["status"], 0) + 1

    user_roles: dict[str, int] = {}
    for item in users:
        user_roles[item["role"]] = user_roles.get(item["role"], 0) + 1

    internal_items = sum(1 for item in library_items if item["visibility"] == "INTERNAL")
    public_items = sum(1 for item in library_items if item["visibility"] == "PUBLIC")

    now = dt.datetime.now().astimezone()
    lines = [
        f"# Dev 试运行基线快照（{now:%Y-%m-%d}）",
        "",
        "## 环境",
        "- Web: `http://127.0.0.1:32080`",
        f"- API: `{base_api}`",
        "- Health: `ok`",
        f"- 采集角色: `{username}`",
        f"- 采集时间: `{now:%Y-%m-%d %H:%M:%S %Z}`",
        "",
        "## 业务基线",
        f"- 线索总数: `{len(leads)}`",
        f"- 已成交客户数: `{len(customers)}`",
        f"- 收费单数: `{len(billings)}`",
        f"- 应收合计: `{billing_summary['total_fee']}`",
        f"- 月费用合计: `{billing_summary['total_monthly_fee']}`",
        f"- 未收合计: `{dashboard['outstanding_amount_total']}`",
        f"- 系统待办数: `{dashboard['system_todo_count']}`",
        f"- 手动待办数: `{dashboard['manual_open_todo_count']}`",
        f"- 常用资料总数: `{len(library_items)}`",
        f"- 常用资料内部/公开: `{internal_items}/{public_items}`",
        f"- 挂靠地址数: `{len(address_resources)}`",
        "",
        "## 线索状态分布",
    ]
    for key in ("NEW", "FOLLOWING", "CONVERTED", "LOST"):
        lines.append(f"- `{key}`: `{lead_status.get(key, 0)}`")

    lines.extend(
        [
            "",
            "## 用户角色分布",
        ]
    )
    for key in ("OWNER", "ADMIN", "MANAGER", "ACCOUNTANT"):
        lines.append(f"- `{key}`: `{user_roles.get(key, 0)}`")

    payment_dist = ", ".join(
        f"{item['payment_method']}={item['count']}" for item in billing_summary["payment_method_distribution"]
    ) or "无"
    status_dist = ", ".join(
        f"{item['status']}={item['count']}" for item in billing_summary["status_distribution"]
    ) or "无"
    receipt_dist = ", ".join(
        f"{item['receipt_account']}={item['payment_count']}笔/{item['total_amount']}"
        for item in billing_summary.get("receipt_account_distribution", [])
    ) or "无"

    lines.extend(
        [
            "",
            "## 收费基线",
            f"- 付款方式分布: `{payment_dist}`",
            f"- 台账状态分布: `{status_dist}`",
            f"- 入账账户分布: `{receipt_dist}`",
            "",
            "## 当前待处理重点",
        ]
    )
    for todo in system_todos:
        lines.append(
            f"- `{todo['module']}` / `{todo['title']}` / 到期 `{todo['due_date']}` / 责任人 `{todo['assignee_username']}`"
        )

    lines.extend(
        [
            "",
            "## 用途",
            "- 后续真实试运行中，如果出现“数量不对”“记录少了/多了”“待办变化异常”，先对比本快照。",
            "- 该快照不是问题记录，不代表需要修复；只作为试运行期间的事实基线。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture a dev trial baseline snapshot from the local API.")
    parser.add_argument("--api-base", default="http://127.0.0.1:32000/api/v1")
    parser.add_argument("--username", default="boss")
    parser.add_argument("--password", default=os.environ.get("DAIZHANG_TRIAL_PASSWORD", "Daizhang#2026!"))
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.output:
        output = Path(args.output)
    else:
        today = dt.date.today().isoformat()
        output = Path("output/test-reports") / f"dev-trial-baseline-{today}.md"

    output.parent.mkdir(parents=True, exist_ok=True)
    content = build_report(args.api_base, args.username, args.password)
    output.write_text(content, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.reason}")
        raise
