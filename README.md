# 账航·一帆财税（SDD 驱动）

## 当前状态
1. 规格文档已落地到 `.sdd/`。
2. 已完成首轮可交互版本：
   - `apps/api`（FastAPI）
   - `apps/web`（Vue3 + Element Plus）
   - `infra/docker-compose.yml`（db/api/web）
3. 当前已支持：
   - 本地账号登录（JWT）
   - 线索列表查询（对齐两套 Excel 模板字段）
   - 新增线索（扩展字段：等级、地区/国家、传真、其他联系方式、服务信息、收费标准、备用字段）
   - 客户开发总览首页精简为核心字段，完整信息进入线索详情
   - 新增跟进 + 跟进历史查看
   - 线索转化为客户（老板/管理员）并自动进入客户档案
   - 转化弹窗可填写转化后的客户名称/联系人/电话，处理线索与客户档案差异
   - 支持撤销转化（若该客户已有关联收费记录则禁止撤销）
   - 线索独立详情页（总览 -> 明细）
   - 客户列表 + 客户档案页（来源线索字段 + 跟进记录 + 档案编辑）
   - 地址资源池（对应 `转化2026.xls` 的 `地址资源`）
   - 收费台账（对齐 `周 (2)`：总费用、月费用、代账周期、到期日、付款方式）
   - 收费记录绑定客户档案（客户选择来自“客户列表”）
   - 收费序号为数字编号（可手填或自动递增），会计归属由客户分配关系继承
   - 台账状态（清账/全欠/部分收费）与已收/未收金额
   - 催收/收款日志（可登记收款、预付、结清）
   - 管理员面板（用户检索、创建、编辑、删除、重置密码）
   - 用户权限边界：管理员可管理全部本地账号，老板仅可管理非管理员账号
   - 用户最近登录时间展示（管理员面板）
   - 操作日志（登录/用户管理/核心业务写操作）
   - LDAP 设置与账号同步（支持群晖 LDAP）

## 本地开发

### 后端
```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 前端
```bash
cd apps/web
npm install
npm run dev
```

## Docker 启动
```bash
cd infra
docker compose up --build
```

说明：
1. `infra/docker-compose.yml` 主要用于本地开发（包含代码挂载、`--reload`）。
2. 基础镜像使用 `docker.1ms.run` 镜像源（`api/web` 均基于 `python`，`db` 基于 `postgres`）。

启动后：
1. Web: `http://localhost:5173`
2. API: `http://localhost:8000`
3. API Health: `http://localhost:8000/api/v1/health`
4. 演示账号：`boss` / `admin` / `accountant` / `accountant2` / `accountant3` / `accountant4`，密码统一 `Demo@12345`

备注：
1. `infra/docker-compose.yml` 默认使用 PostgreSQL（`db` 服务）。
2. 本地直接运行后端时，默认数据库为 SQLite（`apps/api/daizhang.db`）。
3. 可通过环境变量控制启动行为：
   - `BOOTSTRAP_DEMO_DATA=true|false`（是否注入演示数据）
   - `RESET_DB_ON_STARTUP=true|false`（是否启动时重建数据库）

## 群晖 DS920+ 双环境部署（dev + prd）
- 部署文档：`infra/DEPLOY_SYNOLOGY.md`
- 关键文件：
  - `infra/docker-compose.dev.yml`
  - `infra/docker-compose.prd.yml`
  - `.github/workflows/build-and-deploy-synology.yml`

> 说明：`infra/DEPLOY_SYNOLOGY.md` 已按中国大陆网络环境补充企业级部署方案（国内镜像仓库、回滚、备份、监控、安全加固）。
