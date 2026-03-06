# 群晖测试环境部署 Runbook

这份文档记录了本项目在群晖 DS920+ 上完成测试环境部署的实际过程。目标不是写一份泛泛的说明，而是把这次真实走通的链路、踩坑和修复手段固化下来，方便后续正式环境平滑上线。

适用前提：
- 群晖在中国大陆网络环境
- 本次部署的是测试系统，不是正式系统
- 优先走内网 SSH，不把发布链路暴露到公网
- 不依赖 NAS 直接访问 GitHub 或 Gitee

## 1. 本次部署结论

本次测试环境已经在 DS920+ 上跑通，实际验证结果如下：
- Web：`http://192.168.6.6:32080` 返回 `HTTP/1.1 200 OK`
- API：`http://192.168.6.6:32000/api/v1/health` 返回 `{"status":"ok"}`
- 容器：`postgres/api/web` 三个容器均启动成功

本次实测采用的是这条链路：

```text
本机仓库 -> 打包源码 -> 上传 NAS -> NAS 本地经典模式构建 -> docker-compose 启动 -> 健康检查
```

不是这条链路：

```text
GitHub/Gitee -> NAS git clone -> NAS build
```

原因很直接：群晖在大陆网络环境下直接访问代码仓库不稳定，且群晖默认往往没有完整的开发工具链，测试环境优先要可重复、可恢复、可定位问题。

## 2. 实际验证过的环境信息

本次部署时确认过：
- DSM 内网地址：`https://192.168.6.6:5001`
- NAS 内网 IP：`192.168.6.6`
- 机型：DS920+
- 已安装 `Container Manager`
- `docker` 路径：`/usr/local/bin/docker`
- `docker-compose` 路径：`/usr/local/bin/docker-compose`
- `docker-compose` 版本：`v2.9.0`
- SSH 默认关闭，需要临时开启
- 当前用户具备 `sudo` 权限
- NAS 未安装 `git`

## 3. 目录、端口与编排文件

测试环境统一使用：
- 部署目录：`/volume1/docker/daizhang-test`
- 上传包路径：`/volume1/docker/daizhang-synology-src.tar.gz`
- Web 端口：`32080`
- API 端口：`32000`
- PostgreSQL 数据目录：`infra/data/test/postgres`

对应编排文件：
- `infra/docker-compose.test.localbuild.yml`

## 4. 本次实际依赖的关键文件

测试环境这次实际使用了以下文件：
- `infra/docker-compose.test.localbuild.yml`
- `infra/env/api.test.env.example`
- `infra/env/postgres.test.env.example`
- `infra/scripts/package_synology_bundle.sh`
- `apps/api/Dockerfile.prod`
- `apps/web/Dockerfile.test`
- `apps/web/docker/test-static-server.mjs`
- `infra/data/test/postgres/.gitkeep`

说明：
- `apps/web/Dockerfile.test` 只给测试环境使用。
- 正式环境仍建议走标准生产镜像和镜像仓库分发，不建议长期让正式环境也走 NAS 本地源码构建。

## 5. 为什么测试环境不建议 NAS 直接 clone GitHub/Gitee

原因有 4 个：
- 群晖上默认未必有 `git`
- GitHub 在大陆环境下不稳定
- Gitee 虽然可用，但把发布和仓库可达性强绑定了
- 测试环境更需要“可重复部署”，而不是“在 NAS 上临时改代码”

因此测试环境推荐链路是：

```text
本机仓库 -> 打包源码 -> 上传 NAS -> NAS 本地构建镜像 -> 启动容器
```

后续正式环境再升级为：

```text
GitHub/Gitee -> CI 构建镜像 -> 国内镜像仓库 -> NAS 拉镜像发布
```

## 6. 第一次部署前准备

### 6.1 临时开启 SSH

DSM 路径：
- 控制面板
- 终端机和 SNMP
- 启用 SSH 功能

建议：
- 只通过内网 IP 使用 SSH
- 部署完成后关闭 SSH，或至少配合防火墙限制来源 IP

### 6.2 确认 Docker 可用

SSH 登录 NAS 后执行：

```bash
whoami
id
/usr/local/bin/docker --version
/usr/local/bin/docker-compose --version
```

如果普通用户执行 Docker 报权限问题，统一改用：

```bash
sudo /usr/local/bin/docker-compose ...
sudo /usr/local/bin/docker ...
```

## 7. 本机打包源码

在仓库根目录执行：

```bash
./infra/scripts/package_synology_bundle.sh
```

默认会生成：

```bash
output/release/daizhang-synology-src.tar.gz
```

脚本当前会做这些事：
- 排除 `.git`
- 排除 `node_modules`
- 排除 `.venv`
- 排除本地数据库文件
- 排除 `output/release`
- 设置 `COPYFILE_DISABLE=1`
- 设置 `COPY_EXTENDED_ATTRIBUTES_DISABLE=1`

说明：
- macOS 仍可能在解压时出现 `LIBARCHIVE.xattr...` 提示，这次实测不会影响部署结果。
- `infra/data/test/postgres/.gitkeep` 已加入仓库，用来保证测试数据目录能被打进压缩包，避免空目录丢失。

## 8. 上传到 NAS

推荐两种方式：
- `scp`
- DSM File Station 手动上传

目标路径统一为：

```bash
/volume1/docker/daizhang-synology-src.tar.gz
```

## 9. 在 NAS 上解压源码

SSH 到 NAS 后执行：

```bash
mkdir -p /volume1/docker/daizhang-test
rm -rf /volume1/docker/daizhang-test/*
tar -xzf /volume1/docker/daizhang-synology-src.tar.gz -C /volume1/docker/daizhang-test
cd /volume1/docker/daizhang-test
find . -name '._*' -delete
mkdir -p infra/data/test/postgres
```

说明：
- `find . -name '._*' -delete` 用于清理历史压缩包中的 macOS 元数据文件。
- `mkdir -p infra/data/test/postgres` 保留也没问题，即使 `.gitkeep` 已经存在，这条命令仍然安全。

## 10. 创建测试环境变量

在 NAS 上创建：
- `infra/env/postgres.test.env`
- `infra/env/api.test.env`

可以先复制模板：

```bash
cp infra/env/postgres.test.env.example infra/env/postgres.test.env
cp infra/env/api.test.env.example infra/env/api.test.env
```

推荐最小配置如下。

`infra/env/postgres.test.env`

```env
POSTGRES_DB=daizhang_test
POSTGRES_USER=daizhang_test
POSTGRES_PASSWORD=<高强度密码>
```

`infra/env/api.test.env`

```env
APP_NAME=Daizhang API TEST
ENVIRONMENT=test
DATABASE_URL=postgresql+psycopg://daizhang_test:<与上面一致>@postgres:5432/daizhang_test
JWT_SECRET=<至少 32 位随机字符串>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=720
CORS_ALLOW_ORIGINS=http://192.168.6.6:32080,https://192.168.6.6:32080
BOOTSTRAP_DEMO_DATA=true
BOOTSTRAP_DEMO_PASSWORD=<测试演示账号强密码>
RESET_DB_ON_STARTUP=false
```

说明：
- 测试环境可以保留 `BOOTSTRAP_DEMO_DATA=true`
- `BOOTSTRAP_DEMO_PASSWORD` 必须改成你自己的测试密码，不要在登录页展示
- `RESET_DB_ON_STARTUP` 必须保持 `false`
- 如果测试环境改成其他内网地址、内网域名或端口，要同步修改 `CORS_ALLOW_ORIGINS`

## 11. 基础镜像策略

本次在大陆环境下实测更稳定的基础镜像来源：
- `postgres`：华为云 SWR 代理
- `python`：华为云 SWR 代理
- `node`：华为云 SWR 代理
- `npm`：`https://registry.npmmirror.com`
- `pip`：`https://mirrors.aliyun.com/pypi/simple/`

本次实际遇到过：
- `docker.1ms.run/postgres:16-alpine` 返回 `429 Too Many Requests`
- `docker.m.daocloud.io/library/nginx:1.27-alpine` 能解析，但在当前网络下很慢
- 群晖这版 `docker-compose` + BuildKit 对多阶段构建兼容性较差

因此测试环境的前端最终改成：
- 用 `apps/web/Dockerfile.test` 本地构建
- 运行时不依赖 `nginx`
- 直接用 Node 提供静态文件服务

这只是测试环境策略，不是正式环境最终形态。

## 12. 关键点：关闭 BuildKit，使用经典构建

这次真实部署里，群晖 `docker-compose v2.9.0` 在默认 BuildKit 模式下多次卡在：
- `load metadata`
- 第二个 `FROM`
- 前端运行时镜像解析

最终跑通的方式是：

```bash
cd /volume1/docker/daizhang-test
export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0
```

然后再执行构建。

建议测试环境固定使用经典构建：

```bash
cd /volume1/docker/daizhang-test
export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0
sudo -E /usr/local/bin/docker-compose -f infra/docker-compose.test.localbuild.yml build web
sudo -E /usr/local/bin/docker-compose -f infra/docker-compose.test.localbuild.yml up -d
```

## 13. 启动测试环境

完整推荐顺序：

```bash
cd /volume1/docker/daizhang-test
export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0
sudo -E /usr/local/bin/docker-compose -f infra/docker-compose.test.localbuild.yml config
sudo -E /usr/local/bin/docker-compose -f infra/docker-compose.test.localbuild.yml build web
sudo -E /usr/local/bin/docker-compose -f infra/docker-compose.test.localbuild.yml up -d
```

说明：
- `web` 单独先 build，是为了更快暴露构建问题。
- `up -d` 时 PostgreSQL 首次初始化大约需要几十秒。
- `api` 在第一次启动时还会建表并注入演示数据，因此健康检查不要太早打。

## 14. 部署后验证

### 14.1 查看容器状态

```bash
sudo /usr/local/bin/docker-compose -f infra/docker-compose.test.localbuild.yml ps
sudo /usr/local/bin/docker ps
```

预期容器：
- `daizhang-test-postgres`
- `daizhang-test-api`
- `daizhang-test-web`

### 14.2 验证 API 和 Web

```bash
curl -i http://192.168.6.6:32000/api/v1/health
curl -I http://192.168.6.6:32080
curl -i -X POST http://192.168.6.6:32080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  --data '{"username":"not-exists-user","password":"<测试密码>"}'
curl -i -X POST http://192.168.6.6:32080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  --data '{"username":"boss","password":"<测试密码>"}'
```

本次实测结果：

```text
API: HTTP/1.1 200 OK
API Body: {"status":"ok"}
Web: HTTP/1.1 200 OK
Invalid login via Web/API proxy: HTTP/1.1 401 Unauthorized
Valid login via Web/API proxy: HTTP/1.1 200 OK
```

浏览器访问：

```text
http://192.168.6.6:32080
```

### 14.3 查看日志

```bash
sudo /usr/local/bin/docker-compose -f infra/docker-compose.test.localbuild.yml logs --tail=200 postgres
sudo /usr/local/bin/docker-compose -f infra/docker-compose.test.localbuild.yml logs --tail=200 api
sudo /usr/local/bin/docker-compose -f infra/docker-compose.test.localbuild.yml logs --tail=200 web
```

第一次成功启动时，`api` 日志中应出现：

```text
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 15. 本次实际踩到的坑

### 15.1 BuildKit 卡死

表现：
- `docker-compose build web` 长时间停在 metadata 或 stage 切换

处理：
- 关闭 BuildKit
- 使用 `DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0`

### 15.2 空目录丢失导致挂载失败

表现：
- `Bind mount failed: '/volume1/docker/daizhang-test/infra/data/test/postgres' does not exists`

原因：
- 压缩包不会保留空目录

处理：
- 仓库中加入 `infra/data/test/postgres/.gitkeep`
- 解压后额外执行 `mkdir -p infra/data/test/postgres`

### 15.3 API 启动后短时间不响应

表现：
- 容器 `Up`
- 但 `curl /api/v1/health` 返回空响应或连接重置

原因：
- 首次启动时应用还在执行 `startup`：建表 + 演示数据注入

处理：
- 看 `api` 日志是否还停在 `Waiting for application startup.`
- 等待日志出现 `Application startup complete.` 再做健康检查

### 15.4 大陆镜像源不稳定

表现：
- 限流
- 镜像标签不存在
- 拉取耗时过长

处理策略：
- 优先 SWR 代理
- 先手动 `docker pull` 再开始 compose
- 测试环境避免依赖额外运行时镜像

### 15.5 测试前端错误吞掉了 `/api/*` 请求

严重性：
- 高
- 会造成“任意账号看起来都能登录”的假象
- 还会把错误的前端本地状态留在浏览器里

表现：
- 登录页输入不存在的账号，也弹“登录成功”
- 登录后不跳转，或者刷新后进入系统
- 右上角出现类似“会计（未登录）”的矛盾状态
- 页面能看到大量不该在未认证状态下看到的数据

根因：
- 测试环境为了绕开大陆网络问题，用 `apps/web/docker/test-static-server.mjs` 替代了 `nginx`
- 旧版本静态服务对 `/api/*` 没有做反向代理
- 它把 `/api/v1/auth/login` 这类请求也回退成了 `index.html`
- 前端拿到的是 `200 + HTML`，不是 `401/JSON`

修复：
- 测试静态服务必须显式代理 `/api/*` 到 `http://api:8000`
- 非静态资源的 `POST/PUT/DELETE` 不能再回退到 SPA HTML
- 代理失败时返回 `502 Bad Gateway`
- 前端鉴权状态改成“`token` 和 `user` 同时有效才算已登录”
- 前端启动时会调用 `/auth/me` 重新校验浏览器里的会话

复测标准：
- `POST http://192.168.6.6:32080/api/v1/auth/login` 对错误账号返回 `401`
- 浏览器里错误账号必须显示“账号或密码错误”
- 成功登录后必须跳转到业务页
- 刷新后右上角用户名和角色必须保持一致，不允许再出现“未登录”字样

如果再次出现这个现象，优先执行：

```bash
cd /volume1/docker/daizhang-test
export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0
sudo -E /usr/local/bin/docker-compose -f infra/docker-compose.test.localbuild.yml build web
sudo -E /usr/local/bin/docker-compose -f infra/docker-compose.test.localbuild.yml up -d web
sudo /usr/local/bin/docker-compose -f infra/docker-compose.test.localbuild.yml logs --tail=100 web
```

## 16. 回滚与重建

测试环境建议保留简单回滚手段。

停止：

```bash
cd /volume1/docker/daizhang-test
sudo /usr/local/bin/docker-compose -f infra/docker-compose.test.localbuild.yml down
```

完全重建：

```bash
cd /volume1/docker/daizhang-test
sudo /usr/local/bin/docker-compose -f infra/docker-compose.test.localbuild.yml down
rm -rf infra/data/test/postgres/*
export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0
sudo -E /usr/local/bin/docker-compose -f infra/docker-compose.test.localbuild.yml up -d --build
```

注意：
- 测试环境可以重建数据库
- 正式环境不能这么做，正式环境必须走备份、迁移和镜像回滚

## 17. 正式环境怎么平滑升级

这次测试环境已经验证了这 4 件事：
- NAS 路径和端口规划可行
- 大陆镜像源策略可行
- 本机打包 -> NAS 本地发布可行
- 项目可以在群晖上稳定跑起来

后续正式环境建议这样升级：

1. 保持目录结构不变，新建正式环境目录，比如 `/volume1/docker/daizhang-prd`
2. 把正式环境改成“CI 构建镜像 -> 国内镜像仓库 -> NAS 拉镜像发布”
3. 正式环境不要再走 NAS 本地源码 build
4. 正式环境启用备份、镜像版本号、数据库备份与回滚脚本
5. 正式环境前端恢复为标准反向代理运行方式，不继续沿用测试用 Node 静态服务

推荐正式链路：

```text
GitHub/Gitee -> GitHub Actions / Gitee Go / Jenkins -> 阿里云 ACR / 腾讯 TCR / 华为 SWR / Harbor -> NAS docker compose pull && up -d
```

## 18. 安全收尾

测试部署完成后建议执行：
- 关闭 SSH，或至少只允许固定内网来源访问
- 不要把测试端口直接映射到公网
- 正式环境单独做域名、反向代理、证书和防火墙策略

如果后续继续调试，可以保留 SSH；如果当前部署任务结束，优先关闭。
