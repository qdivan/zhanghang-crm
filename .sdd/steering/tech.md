# 技术策略（MVP）

## 总体技术选择
1. 前端：Vue 3 + TypeScript + Vite + Element Plus（中文友好、表格能力强）。
2. 后端：FastAPI + SQLAlchemy + Alembic + Pydantic。
3. 数据库：PostgreSQL（开发期可用 Docker，本地也可直接运行）。
4. 鉴权：JWT（本地账号登录），RBAC（老板/会计/管理员）。
5. 移动端：优先响应式 Web + PWA；后续可封装为 App（Capacitor）。

## 关键技术约束
1. 页面交互以“表格视图 + 抽屉/弹窗编辑”为主，尽量贴近 Excel 心智。
2. API 必须清晰区分周期收费、一次性任务收费、收款流水、成本流水。
3. 所有关键业务操作需要审计字段：创建人、更新时间、操作日志。
4. 导入能力：支持从现有 Excel 批量导入（MVP 至少支持一次性初始化导入）。

## 权限与认证
1. 本地账号：用户名/邮箱 + 密码（bcrypt 哈希）。
2. 角色权限：
   - `OWNER`：全量查看、催款、成本与利润查看。
   - `ADMIN`：账号管理、分配客户、全量数据维护。
   - `ACCOUNTANT`：仅访问自己负责客户与关联账款/催款。
3. LDAP（二期）：预留认证提供者接口，支持对接群晖 LDAP。

## 部署策略
1. 开发环境：Docker Compose（一键启动前后端和数据库）。
2. 生产环境（预期）：同样可用 Compose 在 NAS/服务器部署。
3. 备份：数据库定时备份 + 导出 CSV。

## 质量与测试
1. 后端：pytest（服务层、权限、账款计算规则）。
2. 前端：Vitest + Playwright（关键页面流程）。
3. 验收：对照 `.sdd/specs/<spec>/requirements.md` 的 checklist 逐项通过。
