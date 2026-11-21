# Exchange provider mock

The exchange-provider mock implements the external contract consumed by the
Exchange adapter. It returns fixed fixtures and can be switched into predictable
failure modes for resilience tests. Its rates are not live financial data.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `8080` | HTTP listen port. |
| `MOCK_MODE` | `ok` | Initial response mode. |
| `MOCK_API_KEY` | Unset | When set, requires `Authorization: Bearer <key>`. |

## Endpoints

| Method and path | Behavior |
| --- | --- |
| `GET /health` | Returns the liveness status. |
| `GET /latest` | Returns rates for `base` and comma-separated `symbols`. |
| `GET /v1/latest` | Provider-compatible alias for `/latest`. |
| `GET /latest.json` | Provider-compatible alias for `/latest`. |
| `GET /control` | Returns the active mode. |
| `POST /control?mode=...` | Changes the active mode for later requests. |

`base` defaults to `USD` and `symbols` defaults to `EUR`. Supported currencies
are USD, EUR, BRL, GBP, and JPY. Values are derived from fixed USD-relative
fixtures and returned as a `bid`/`ask` pair. The observation timestamp is also
fixed so tests remain deterministic.

```bash
curl 'http://localhost:8080/latest?base=USD&symbols=EUR,BRL'
```

## Failure modes

| Mode | Response |
| --- | --- |
| `ok` | Normal fixture response. |
| `error` | HTTP `503` provider unavailable response. |
| `timeout` | Delays the response by five seconds. |
| `malformed` | HTTP `200` with a non-JSON body. |
| `rate_limit` | HTTP `429` with `Retry-After: 2`. |
| `unsupported` | HTTP `400` unsupported-currency response. |

Change modes without restarting the process:

```bash
curl -X POST 'http://localhost:8080/control?mode=rate_limit'
```

The control endpoint is intentionally unauthenticated because this service is a
local test fixture. That is another reason it must not be exposed or deployed.
