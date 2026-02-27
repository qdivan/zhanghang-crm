# 群晖 DS920+ 企业级部署指南（中国大陆网络版）

本文档适用于当前项目在同一台群晖上运行 `dev` 与 `prd` 双环境，并通过 GitHub/Gitee 流水线自动构建和部署。

## 1. 部署目标
- 同机双环境：`dev`、`prd` 隔离部署。
- 可回滚：每次部署对应唯一镜像标签（`commit sha`）。
- 适配中国大陆网络：避免 NAS 强依赖访问 GitHub/GHCR。
- 安全合规：最小权限、密钥分离、可审计。

## 2. 推荐架构（中国大陆）
- 代码仓库：GitHub 或 Gitee。
- CI 构建机：
  - 方案 A：GitHub Actions 托管 Runner。
  - 方案 B：自建 Runner（大陆云主机/办公室服务器），稳定性更高。
- 镜像仓库：优先国内仓库（阿里云 ACR / 腾讯 TCR / 华为 SWR / 私有 Harbor）。
- 部署目标：群晖 DS920+（Container Manager）。
- 反向代理与 TLS：群晖反向代理或 Nginx Proxy Manager。

说明：本仓库的 workflow 已支持可配置镜像仓库，不再强制 GHCR。

## 3. 环境隔离设计
- `infra/docker-compose.dev.yml`
  - 端口：`32080(web)`、`32000(api)`
  - 数据目录：`./data/dev/*`
- `infra/docker-compose.prd.yml`
  - 端口：`31080(web)`、`31000(api)`
  - `prd` 独立 PostgreSQL：`./data/prd/postgres`

建议：
- `dev` 使用测试域名（如 `dev-xxx.example.com`）。
- `prd` 使用正式域名（如 `crm.example.com`）。

## 4. 群晖初始化（一次性）
1. 安装并启用：`Container Manager`、`SSH`。
2. 创建目录（示例）：
```bash
mkdir -p /volume1/docker/daizhang
```
3. 将项目放到该目录（`git clone` 或文件同步均可）。
4. 准备环境变量：
```bash
cd /volume1/docker/daizhang
cp infra/env/api.dev.env.example infra/env/api.dev.env
cp infra/env/api.prd.env.example infra/env/api.prd.env
cp infra/env/postgres.prd.env.example infra/env/postgres.prd.env
```
5. 修改生产密钥（必须）：
- `infra/env/api.prd.env` 的 `JWT_SECRET`。
- `infra/env/postgres.prd.env` 的数据库密码。
- `CORS_ALLOW_ORIGINS` 改为你的正式域名。

## 5. CI/CD（GitHub Actions）配置
工作流文件：
- `.github/workflows/build-and-deploy-synology.yml`

### 5.1 必填 Secrets
- `NAS_HOST`
- `NAS_PORT`
- `NAS_USER`
- `NAS_SSH_KEY`
- `NAS_APP_DIR`（例如 `/volume1/docker/daizhang`）

### 5.2 镜像仓库凭据（使用国内仓库时必填）
- `REGISTRY_USERNAME`
- `REGISTRY_PASSWORD`

### 5.3 可选 Secrets（GHCR 私有仓库才需要）
- `GHCR_READ_PACKAGES_TOKEN`

### 5.4 可选 Variables（强烈建议）
- `REGISTRY_HOST`
  - 示例：`registry.cn-hangzhou.aliyuncs.com`
  - 默认：`ghcr.io`
- `IMAGE_NAMESPACE`
  - 示例：`your-company/daizhang`
  - 最终镜像会是：
    - `${REGISTRY_HOST}/${IMAGE_NAMESPACE}/daizhang-api`
    - `${REGISTRY_HOST}/${IMAGE_NAMESPACE}/daizhang-web`
- `NAS_GIT_SYNC`
  - `false`（默认，推荐）
  - `true`（每次部署前在 NAS 上执行 `git pull`）

说明：大陆场景建议 `NAS_GIT_SYNC=false`，避免 NAS 端访问 GitHub 不稳定导致部署失败。

## 6. 分支与发布策略（企业推荐）
- `develop`：自动部署到 `dev`。
- `main`：自动部署到 `prd`。
- 可选：只允许通过 PR 合并到 `main`，并开启保护分支。

建议增加门禁：
- 后端测试通过才允许合并。
- 前端构建通过才允许合并。
- 镜像扫描（Trivy）通过才允许部署 `prd`。

## 7. 首次部署与日常发布
### 7.1 首次手动验证
```bash
cd /volume1/docker/daizhang
./infra/scripts/deploy.sh dev <api_image> <web_image>
./infra/scripts/deploy.sh prd <api_image> <web_image>
```

### 7.2 自动发布
- 推送 `develop` -> 自动部署 `dev`。
- 推送 `main` -> 自动部署 `prd`。

## 8. 回滚策略（必须演练）
1. 找到上一个稳定版本镜像标签（建议用 `commit sha` 标签）。
2. 在 NAS 执行：
```bash
cd /volume1/docker/daizhang
./infra/scripts/deploy.sh prd <api_old_tag> <web_old_tag>
```
3. 验证接口健康检查与核心页面。

建议每月做一次“演练式回滚”。

## 9. 数据安全与备份
- PostgreSQL：
  - 每日 `pg_dump`（至少保留 7~30 天）。
  - 数据目录快照（Btrfs Snapshot Replication）。
- 应用配置：
  - `infra/env/*.env` 做加密备份。
- 异地备份：
  - 关键备份同步到异地对象存储。

## 10. 监控与告警（企业最小集）
- 容器健康：`docker ps`、容器重启次数。
- 资源指标：CPU / 内存 / 磁盘。
- 日志：保留 7~14 天，错误关键字告警。
- 可选：Prometheus + Grafana + Loki。

## 11. 安全加固清单
- 关闭默认口令、使用高强度随机密钥。
- SSH 禁止密码登录，仅密钥登录。
- 生产环境 `BOOTSTRAP_DEMO_DATA=false`。
- 最小开放端口，仅暴露反向代理入口。
- 使用 HTTPS，并定期更新证书。
- 定期更新基础镜像与系统补丁。

## 12. Gitee 接入方案
### 方案 A（推荐）
- Gitee 仅做代码托管。
- 镜像/部署统一走 GitHub Actions（配置国内镜像仓库）。

### 方案 B
- 用 Gitee Go / Jenkins 执行与 GitHub 相同的部署命令：
```bash
./infra/scripts/deploy.sh <dev|prd> <api_image> <web_image>
```

核心原则：仓库平台可变，部署脚本与运行架构保持一致。
