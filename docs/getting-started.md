# Getting started

## Prerequisites

Choose one of the following:

- Docker, when the parent platform or standalone service Compose file builds
  the mock images; or
- Python 3.12 or newer, when running a server or the regression suite directly.

No third-party Python packages are needed by the mock services.

## Run a server directly

Each mock is a standalone Python entry point. Run it from the repository root.

### Identity

```bash
JWT_SECRET=local-secret python identity/server.py
```

### Image storage

```bash
IMAGE_STORAGE_DATA_DIR=.local/image-data python image-storage/server.py
```

### Exchange provider

```bash
python exchange-provider/server.py
```

The identity and exchange-provider mocks listen on port `8080` by default. The
image-storage mock listens on `8090`.

## Verify a service

All mocks expose a health endpoint:

```bash
curl http://localhost:8080/health
```

For image storage, use port `8090`.

## Use Docker

The parent platform and standalone service repositories reference these
directories as Compose build contexts. To inspect or run one image by itself:

```bash
docker build -t local-identity-mock identity
docker run --rm -p 8080:8080 -e JWT_SECRET=local-secret local-identity-mock
```

Prefer the relevant Compose file when exercising an end-to-end flow because it
provides the URLs, shared secrets, volumes, and service dependencies expected by
the consuming application.

## Production guard

The following command must exit before opening a network port:

```bash
ENV=production python identity/server.py
```

The same guard applies to every mock and also checks `APP_ENV`. Do not weaken or
bypass this protection.
