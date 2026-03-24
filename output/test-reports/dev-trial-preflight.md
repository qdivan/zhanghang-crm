# Dev 试运行前检查

## 基线
- 提交：`732cbf1`
- 计划：`/Users/shangyifan/Documents/New project/.sdd/specs/2026-02-26-daizhang-mvp/execution-plan-release-readiness.md`
- 检查时间：`2026-03-25`

## 已确认通过
1. Git 远端同步
- `origin/main` 已同步到 `732cbf1`

2. Docker 环境
- 本机 `docker` 与 `docker compose` 可用
- 32000 / 32080 端口当前空闲，可用于 dev 试运行

3. 代码与验收状态
- `UAT Round 1`：通过
- `UAT Round 2`：通过
- 当前适合进入 dev 试运行

## 当前阻塞项
1. dev 环境变量文件缺失
- 缺少：`/Users/shangyifan/Documents/New project/infra/env/api.dev.env`
- 当前只有模板：`/Users/shangyifan/Documents/New project/infra/env/api.dev.env.example`
- 结论：部署前必须在目标机器上复制模板并填写真实值

2. dev compose 默认镜像仍是占位镜像
- 文件：`/Users/shangyifan/Documents/New project/infra/docker-compose.dev.yml`
- 当前默认值：
  - `ghcr.io/your-org/daizhang-api:dev-latest`
  - `ghcr.io/your-org/daizhang-web:dev-latest`
- 结论：试运行前必须明确实际镜像来源，或改用本地构建方案

## 建议执行顺序
1. 在目标 dev 机器创建 `infra/env/api.dev.env`
2. 明确 `API_IMAGE` / `WEB_IMAGE` 实际值
3. 执行 `docker compose -f infra/docker-compose.dev.yml up -d`
4. 验证：
- `http://<host>:32080`
- `http://<host>:32000/api/v1/health`
5. 让老板 + 1 位会计开始连续试用

## 结论
- 当前不是业务阻塞，而是部署准备阻塞。
- 代码和 UAT 已经到位；要继续推进，下一步应进入 `dev 部署执行计划`，而不是继续做产品功能。
