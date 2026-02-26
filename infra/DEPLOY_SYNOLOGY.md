# Synology DS920+ Deployment Guide (dev + prd)

## 1. Overall architecture
- `develop` branch -> build image tag `dev-latest` -> deploy to NAS `dev` stack
- `main` branch -> build image tag `prd-latest` -> deploy to NAS `prd` stack
- `dev` and `prd` run on the same DS920+, isolated by different compose projects, ports, and data directories

## 2. Required NAS preparation
1. In DSM, install `Container Manager` and enable SSH.
2. Create deployment directory (example):
   - `/volume1/docker/daizhang`
3. Clone this repository into that directory.
4. Create runtime env files from templates:
```bash
cd /volume1/docker/daizhang
cp infra/env/api.dev.env.example infra/env/api.dev.env
cp infra/env/api.prd.env.example infra/env/api.prd.env
cp infra/env/postgres.prd.env.example infra/env/postgres.prd.env
```
5. Edit these three `.env` files and replace all placeholder secrets.

## 3. Port plan on same NAS
- `prd web`: `31080`
- `prd api`: `31000`
- `dev web`: `32080`
- `dev api`: `32000`

If you use Synology reverse proxy, map domains to these container ports.

## 4. GitHub Actions CI/CD
Workflow file already exists:
- `.github/workflows/build-and-deploy-synology.yml`

Set these repository secrets in GitHub:
- `NAS_HOST`: NAS IP or domain
- `NAS_PORT`: SSH port (usually `22`)
- `NAS_USER`: SSH username
- `NAS_SSH_KEY`: private key for SSH deploy
- `NAS_APP_DIR`: deploy path on NAS (example `/volume1/docker/daizhang`)
- `GHCR_READ_PACKAGES_TOKEN`: optional, required when GHCR package is private

After that:
- push `develop` -> auto deploy `dev`
- push `main` -> auto deploy `prd`

## 5. First-time manual deploy (optional)
After env files are ready on NAS:
```bash
cd /volume1/docker/daizhang
./infra/scripts/deploy.sh dev ghcr.io/<owner>/daizhang-api:dev-latest ghcr.io/<owner>/daizhang-web:dev-latest
./infra/scripts/deploy.sh prd ghcr.io/<owner>/daizhang-api:prd-latest ghcr.io/<owner>/daizhang-web:prd-latest
```

## 6. About Gitee pipeline
Recommended options:
1. Mirror Gitee repo to GitHub and use this GitHub Actions workflow for deployment.
2. Use Gitee Go/Jenkins and execute the same NAS command:
```bash
./infra/scripts/deploy.sh <dev|prd> <api_image> <web_image>
```

So Git provider can be GitHub or Gitee, while deploy logic stays identical.
