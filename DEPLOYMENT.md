# Deployment guide

The supported deployment unit is Docker Compose. It runs the React production build and FastAPI API in one container, a separate analysis worker, and MongoDB on a private container network.

MongoDB must run on an operating system and kernel supported by the pinned server release. MongoDB currently documents a TCMalloc incompatibility for Linux kernels 6.19 through 7.0.13. Its stable server builds can also reject newer, already-fixed kernels until the corresponding MongoDB startup-check patch is released. If `mongod` reports this guard, deploy on a supported LTS kernel, use MongoDB Atlas, or upgrade to a stable MongoDB patch that explicitly includes `SERVER-125742`; do not bypass the safety check.

## 1. Prepare secrets

Copy `.env.example` to `.env`. Generate two different secrets:

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

Set the first as `MONGO_ROOT_PASSWORD` and the second as `MONGO_APP_PASSWORD`. Keep both values hexadecimal so they are safe inside the MongoDB connection URI. Never commit `.env`.

For a localhost or private-network demonstration, keep `COOKIE_SECURE=false` and list the exact HTTP browser origin in `ALLOWED_ORIGINS`.

For an internet deployment:

- terminate TLS at a trusted reverse proxy or platform ingress;
- set `COOKIE_SECURE=true`;
- set `ALLOWED_ORIGINS` to the exact public HTTPS origin, with no trailing slash;
- keep MongoDB and the worker off public ports;
- persist and back up the `mongo_data` volume;
- configure ingress request-size and rate limits.

## 2. Validate

Install the native development prerequisites described in `README.md`, then run:

```bash
./scripts/preflight.sh
```

The script checks backend imports, runs the regression suite, performs a locked frontend install and production build, and validates the Compose file when Docker is installed.

For a saved release copy, verify the checked-in project files against the supplied manifest:

```bash
sha256sum --check SHA256SUMS
```

## 3. Start

```bash
docker compose up --build -d
docker compose ps
docker compose exec api python -m app.manage create-admin \
  --email admin@your-team.org --name 'Team administrator'
```

Open the origin configured in `.env`. The default is `http://127.0.0.1:8080`.

The API connects as `sentinel_app`, which has read/write access only to the `bitcoin_sentinel` database. The MongoDB root credential is used only for database administration. The application user is created when the database volume is initialized for the first time.

## 4. Operate and verify

```bash
curl --fail http://127.0.0.1:8080/api/health
docker compose logs --tail=100 api worker mongo
```

A healthy response is:

```json
{"status":"ok","database":"mongodb"}
```

Use `docker compose restart` for ordinary restarts. Do not run `docker compose down -v` unless you intentionally want to delete the database volume.

When changing `MONGO_APP_PASSWORD` after initial deployment, update the MongoDB user password inside the database as well; initialization scripts do not rerun on an existing volume.
