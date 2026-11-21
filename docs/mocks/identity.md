# Identity mock

The identity mock issues short-lived HS256 JSON Web Tokens for the Product
standalone stack. It signs tokens with the same `JWT_SECRET` used by the Product
service, allowing authentication flows to run without a real identity provider.

## Configuration

| Variable | Required | Purpose |
| --- | --- | --- |
| `JWT_SECRET` | Yes | Secret used to sign HS256 tokens. Requests return `500` when it is absent. |

The server listens on port `8080`.

## Endpoints

### `GET /health`

Returns HTTP `200` with the service status:

```json
{"status":"UP"}
```

### `POST /token`

Creates a token from a JSON object:

```bash
curl -X POST http://localhost:8080/token \
  -H 'Content-Type: application/json' \
  -d '{"sub":"0195ae95-5be7-7dd3-b35d-7a7d87c404fb","roles":["ROLE_ADMIN"]}'
```

Request fields:

| Field | Default | Rules |
| --- | --- | --- |
| `sub` | Random UUID | Converted to a string; an empty value receives a random UUID. |
| `roles` | `["ROLE_ADMIN"]` | Must be a list containing only strings. |
| `ttl_seconds` | `3600` | Integer or integer string, clamped to `60`–`86400`. Booleans are rejected. |

The body must be a JSON object no larger than 64 KiB. A successful response
contains `access_token`, `token_type`, and `expires_in`. The token claims include
`sub`, `roles`, `iss`, `iat`, and `exp`; `iss` is always
`local-identity-mock`.

Malformed JSON, an invalid body shape, invalid roles, or an invalid TTL returns
HTTP `400` with code `INVALID_REQUEST`.
