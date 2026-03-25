# 安全性与性能测试计划（Dev 试运行补充）

## Summary
- 在当前 `dev` 试运行体系之外，新增一份并行的“安全性 + 性能”专项测试计划。
- 目标：
  - 验证当前权限、认证、公开/内部数据边界没有明显漏洞。
  - 验证关键页面在桌面和移动端没有明显卡顿，并把“卡不卡”量化。
- 本轮只新增计划、日志模板和辅助脚本，不改业务接口、不改数据模型、不扩功能。
- 当前默认测试环境：
  - Web：`http://127.0.0.1:32080`
  - API：`http://127.0.0.1:32000/api/v1`

## 固定产物
- 计划：`/Users/shangyifan/Documents/New project/.sdd/specs/2026-02-26-daizhang-mvp/execution-plan-security-performance.md`
- 安全日志：`/Users/shangyifan/Documents/New project/output/test-reports/security-test-log.md`
- 性能日志：`/Users/shangyifan/Documents/New project/output/test-reports/performance-test-log.md`
- 汇总结论：`/Users/shangyifan/Documents/New project/output/test-reports/security-performance-summary.md`
- API 采样脚本：`/Users/shangyifan/Documents/New project/scripts/run_api_perf_sample.py`

## 安全性测试范围
1. 认证与会话
- 本地账号错误密码、IP 锁定、锁定后恢复
- 停用账号、删除账号、错误 token、退出登录后访问受保护页面
- 本地账号和 LDAP 账号路径不串线

2. 权限与数据边界
- 角色矩阵固定为：`OWNER / ADMIN / MANAGER / ACCOUNTANT`
- `MANAGER` 只能看直属下属范围内的线索、客户、收费、到账核对
- `ACCOUNTANT` 默认不能看管理员面板、到账核对；只有显式授权时才可访问
- `common-library-items/public` 只能返回公开资料，不能泄漏内部资料字段

3. 直接 API 访问
- 受保护接口统一做：`未登录 / 低权限 / 越权 ID`
- 重点接口：
  - `/leads`
  - `/customers`
  - `/billing-records`
  - `/billing-records/receipt-account-ledger`
  - `/users`
  - `/admin/*`

4. 输入与输出硬化
- 备注、常用资料、客户事项等文本字段插入 HTML/脚本片段，验证前端只按纯文本展示
- 日期、空 payload、非法 ID、重复公司名、越权客户 ID 等异常输入必须返回受控错误，不允许 `500`
- 日志与错误信息中不得出现密码、token、LDAP 凭据

5. 安全记录规则
- 每个失败项必须写入 `security-test-log.md`
- 记录格式固定：`编号 / 场景 / 角色 / 接口或页面 / 操作 / 期望 / 实际 / 严重级别 / 证据 / 状态`
- 分级：
  - `P0`：越权读写、认证失效、公开泄漏内部数据
  - `P1`：权限边界不一致、错误信息泄漏、锁定逻辑失效
  - `P2`：安全提示、审计细节或回退体验不足

## 性能测试范围
1. API 性能
- 固定采样接口：
  - `/dashboard/summary`
  - `/leads`
  - `/customers`
  - `/billing-records`
  - `/billing-records/summary`
  - `/dashboard/system-todos`
- 可选明细接口：
  - `/customers/{id}`
  - `/billing-records/ledger`
  - `/billing-records/receipt-account-ledger`
- 默认每个接口采样 `20` 次，记录：
  - `count`
  - `p50_ms`
  - `p95_ms`
  - `max_ms`
  - `failures`

2. 前端交互性能
- 固定页面：
  - 登录页
  - 客户开发
  - 客户档案
  - 收费明细
  - 到账核对
  - 常用资料
- 固定设备：
  - 桌面 `1440x900`
  - 移动 `390x844`
- 固定场景：
  - 登录后首屏可用时间
  - 页面路由切换到“首个核心数据可见”
  - 客户开发筛选提交
  - 客户档案打开
  - 收费明细筛选
  - 收费明细展开往来账
  - 到账核对切换入账账户
  - 常用资料搜索

3. 性能阈值
- API：
  - 列表/汇总接口：`p95 <= 500ms`
  - 明细/台账接口：`p95 <= 800ms`
  - `failures = 0`
- 前端桌面：
  - 路由到可用界面：`<= 1.5s`
  - 筛选、展开、抽屉打开：`<= 300ms`
- 前端移动：
  - 路由到可用界面：`<= 2.5s`
  - 筛选、展开、抽屉打开：`<= 500ms`
- 交互卡顿判定：
  - 不允许连续可感知卡顿 `> 1s`
  - 不允许长任务 `> 500ms`
  - 若 `200ms ~ 500ms` 长任务频繁出现，记为 `P2`

4. 性能记录规则
- API 采样输出写 JSON
- 页面交互结果写 `performance-test-log.md`
- 页面卡顿问题必须附截图或 trace 路径
- 最终结论汇总到 `security-performance-summary.md`

## 执行顺序
1. 先跑 API 性能采样，形成基线
2. 再跑桌面端性能与安全矩阵
3. 再跑移动端性能与关键权限页面
4. 最后汇总所有问题，按 `P0/P1/P2` 归类
5. 若出现 `P0/P1`，暂停继续试运行，先修问题；若只有 `P2`，进入专项优化轮

## 当前执行状态（2026-03-25）
- API 性能采样：`DONE`
- 安全矩阵第 1 轮：`DONE`
- 前端性能第 1 轮：`DONE`
- 前端性能针对性优化与复测：`DONE`
- 当前结果：
  - 安全：`PASS 14 / FAIL 0`
  - 性能：`PASS`
  - 分级：`P0 0 / P1 0 / P2 0`
- 当前未阻塞 `dev` 试运行。

## Assumptions
- 当前测试环境默认为本机 `dev`，不切 Synology，不切生产。
- 不引入 `k6`、`lighthouse` 等当前未就绪工具；只用仓库现有能力和本机已有工具：`python3`、`requests/httpx`、`pytest`、`playwright-cli`。
- 本轮关注“应用安全”和“用户可感知性能”，不做大规模压测、DoS 或基础设施渗透测试。
- 真实试运行反馈仍继续写入 `/Users/shangyifan/Documents/New project/output/test-reports/dev-trial-feedback-log.md`；安全/性能专项结果单独写新日志，最后汇总到 summary。
