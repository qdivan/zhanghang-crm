# Dev 试运行部署结果

## 基线
- 提交：`25531c7`
- 执行计划：`/Users/shangyifan/Documents/New project/.sdd/specs/2026-02-26-daizhang-mvp/execution-plan-dev-deploy.md`
- 部署时间：`2026-03-25`

## 本次执行
1. 已创建 dev 环境变量文件
- 使用：`/Users/shangyifan/Documents/New project/infra/env/api.dev.env`
- 当前口径：本地 dev / SQLite / 演示数据开启

2. 已把 dev compose 调整为默认可本地构建
- 文件：`/Users/shangyifan/Documents/New project/infra/docker-compose.dev.yml`
- 当前默认镜像：
  - `daizhang-api:dev-local`
  - `daizhang-web:dev-local`

3. 已执行启动
```bash
docker compose -f /Users/shangyifan/Documents/New project/infra/docker-compose.dev.yml up -d --build
```

## 验证结果
1. 容器
- `daizhang-dev-api`：运行中
- `daizhang-dev-web`：运行中

2. 健康检查
- API：`http://127.0.0.1:32000/api/v1/health` -> `{"status":"ok"}`
- Web：`http://127.0.0.1:32080` -> `HTTP 200`

3. 浏览器 smoke
- 登录页可打开：`http://127.0.0.1:32080/login`
- 使用 `boss / Daizhang#2026!` 可登录成功
- 登录后进入：`http://127.0.0.1:32080/leads`

## 当前可用于试运行
- Web：`http://127.0.0.1:32080`
- API：`http://127.0.0.1:32000`
- Health：`http://127.0.0.1:32000/api/v1/health`

## 已知说明
1. 当前 dev 是本地构建运行，不依赖远端镜像仓库
2. 当前 `api.dev.env` 为本地开发用配置，不应提交仓库
3. Docker 启动时出现 `linux/amd64` 与宿主 `arm64` 的平台提示，但本次服务已正常运行；若后续长期本机试运行，再考虑单独收掉平台警告

## 下一步
1. 让老板和 1 位会计直接进入 `32080` 开始试运行
2. 试运行期间按真实问题记录反馈
3. 若试运行稳定，再进入群晖 dev 环境部署
