# Development

## Run the regression suite

The tests use only the Python standard library and start each HTTP handler on an
ephemeral local port:

```bash
python -m unittest discover -s tests -v
```

The suite covers token signing and validation, the image object lifecycle,
invalid uploads, exchange-provider aliases and failure modes, and production
startup guards.

## Preview these docs

Create a virtual environment, install the pinned documentation dependency, and
start the development server:

```bash
python -m venv .venv
python -m pip install -r requirements-docs.txt
python -m mkdocs serve
```

Open `http://127.0.0.1:8000`. Before committing documentation changes, run:

```bash
python -m mkdocs build --strict
```

The generated `site/` directory is a build artifact and should not be
committed.

## Change checklist

When changing a mock contract:

1. Keep the response deterministic; do not call a real external service.
2. Preserve the production startup guard.
3. Add or update regression coverage in `tests/test_mocks.py`.
4. Update the relevant page under `docs/mocks/` and its local README.
5. Run both the regression suite and the strict documentation build.
