# 性能测试日志

## 环境
- Web：`http://127.0.0.1:32080`
- API：`http://127.0.0.1:32000/api/v1`
- 计划：`/Users/shangyifan/Documents/New project/.sdd/specs/2026-02-26-daizhang-mvp/execution-plan-security-performance.md`

## API 采样结果
- 输出 JSON 路径：`/Users/shangyifan/Documents/New project/output/test-reports/api-perf-sample-2026-03-25.json`
- 采样命令：
```bash
python3 /Users/shangyifan/Documents/New project/scripts/run_api_perf_sample.py \
  --base-url http://127.0.0.1:32000/api/v1 \
  --username boss \
  --password 'Daizhang#2026!' \
  --iterations 20 \
  --output /tmp/api-perf-sample.json
```

### 第 1 轮 API 基线
| 接口 | p95 | max | failures | 结论 |
| --- | --- | --- | --- | --- |
| `/dashboard/summary` | `60.43ms` | `219.50ms` | `0` | 通过 |
| `/leads` | `17.73ms` | `23.62ms` | `0` | 通过 |
| `/customers` | `44.62ms` | `81.05ms` | `0` | 通过 |
| `/billing-records` | `21.67ms` | `24.30ms` | `0` | 通过 |
| `/billing-records/summary` | `28.18ms` | `66.35ms` | `0` | 通过 |
| `/dashboard/system-todos` | `23.25ms` | `31.29ms` | `0` | 通过 |

### 第 1 轮页面交互结论
- 原始结果：`/Users/shangyifan/Documents/New project/output/test-reports/frontend-perf-sample-2026-03-25.json`
- 结果总览：`PASS 10 / FAIL 2`
- 说明：本轮是 `playwright-cli` 墙钟时间基线，适合作为“是否明显卡顿”的第一轮筛查；若后续继续优化，可再补更细的 trace。

### 第 2 轮针对性复测
- 复测方式：浏览器内 `performance.now()` 计时，剔除 CLI 包装开销。
- 复测证据：
  - `/Users/shangyifan/Documents/New project/output/test-reports/performance-retest-login-2026-03-25.txt`
  - `/Users/shangyifan/Documents/New project/output/test-reports/performance-retest-ledger-2026-03-25.txt`
- 复测结果：
  - `客户开发登录后首屏可用 = 315.50ms`
  - `收费明细展开往来账 = 72.90ms`
- 结论：此前两条 `P2` 已通过优化和复测收口。

## 页面交互记录
| 编号 | 日期 | 设备 | 页面 | 场景 | 阈值 | 实际 | 结论 | 证据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `P-D-001` | `2026-03-25` | 桌面 | 登录页 | 首屏可用 | `<= 1.5s` | `74.26ms` | 通过 | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-25T02-08-28-326Z.yml` |
| `P-D-002` | `2026-03-25` | 桌面 | 客户开发 | 登录后首屏可用 | `<= 1.5s` | `2292.90ms -> 315.50ms` | 已收口 | `/Users/shangyifan/Documents/New project/output/test-reports/performance-retest-login-2026-03-25.txt` |
| `P-D-003` | `2026-03-25` | 桌面 | 客户档案 | 路由打开客户档案 | `<= 1.5s` | `573.30ms` | 通过 | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-25T02-08-33-423Z.yml` |
| `P-D-004` | `2026-03-25` | 桌面 | 收费明细 | 路由打开收费明细 | `<= 1.5s` | `705.33ms` | 通过 | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-25T02-08-34-129Z.yml` |
| `P-D-005` | `2026-03-25` | 桌面 | 收费明细 | 展开往来账（海恩诺） | `<= 300ms` | `2799.29ms -> 72.90ms` | 已收口 | `/Users/shangyifan/Documents/New project/output/test-reports/performance-retest-ledger-2026-03-25.txt` |
| `P-D-006` | `2026-03-25` | 桌面 | 到账核对 | 路由打开到账核对 | `<= 1.5s` | `584.04ms` | 通过 | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-25T02-08-37-514Z.yml` |
| `P-D-007` | `2026-03-25` | 桌面 | 常用资料 | 路由打开常用资料 | `<= 1.5s` | `452.44ms` | 通过 | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-25T02-08-37-965Z.yml` |
| `P-M-001` | `2026-03-25` | 移动 | 登录页 | 首屏可用 | `<= 2.5s` | `79.77ms` | 通过 | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-25T02-08-40-693Z.yml` |
| `P-M-002` | `2026-03-25` | 移动 | 客户开发 | 登录后首屏可用 | `<= 2.5s` | `2200.42ms` | 通过 | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-25T02-08-45-119Z.yml` |
| `P-M-003` | `2026-03-25` | 移动 | 收费明细 | 路由打开收费明细 | `<= 2.5s` | `533.66ms` | 通过 | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-25T02-08-45-652Z.yml` |
| `P-M-004` | `2026-03-25` | 移动 | 客户列表 | 路由打开客户列表 | `<= 2.5s` | `441.46ms` | 通过 | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-25T02-08-46-094Z.yml` |
| `P-M-005` | `2026-03-25` | 移动 | 常用资料 | 路由打开常用资料 | `<= 2.5s` | `389.47ms` | 通过 | `/Users/shangyifan/Documents/New project/.playwright-cli/page-2026-03-25T02-08-46-484Z.yml` |

## 当前性能结论
- `P0`：0
- `P1`：0
- `P2`：0
- 当前不阻塞继续试运行。

## 阈值
- API 列表/汇总：`p95 <= 500ms`
- API 明细/台账：`p95 <= 800ms`
- 前端桌面路由：`<= 1.5s`
- 前端移动路由：`<= 2.5s`
- 前端桌面交互：`<= 300ms`
- 前端移动交互：`<= 500ms`
- 长任务：`> 500ms` 记问题
