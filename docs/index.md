# Local mocks

This repository contains deterministic stand-ins for external services used by
the Microsserv52 platform during local development and continuous integration.
They make the integration stack repeatable without requiring third-party
accounts, credentials, or live network dependencies.

!!! danger "Local and CI use only"
    These services are not production emulators and must never be deployed to a
    production environment. Every entry point refuses to start when `ENV` or
    `APP_ENV` is set to `prod` or `production`.

## Available services

| Mock | Default port | Purpose |
| --- | ---: | --- |
| [Identity](mocks/identity.md) | `8080` | Issues deterministic-contract HS256 tokens for the Product service. |
| [Image storage](mocks/image-storage.md) | `8090` | Emulates the object lifecycle used for product images. |
| [Exchange provider](mocks/exchange-provider.md) | `8080` | Returns fixed exchange rates and controlled failure responses. |

The mocks use only the Python standard library. Their Docker images therefore
do not need application dependencies, and the regression suite can run without
external services.

## Choose a path

- [Run the mocks locally](getting-started.md)
- [Understand and test each HTTP contract](mocks/identity.md)
- [Contribute safely](development.md)
