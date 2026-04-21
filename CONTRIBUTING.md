# Contributing to open-inventory

Thank you for your interest in contributing to open-inventory! This document outlines our contribution process and expectations.

## Licensing

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. By contributing to this project, you agree that your contributions will be licensed under the same license. See `LICENSE` for the full text.

## Getting Started

### Prerequisites

- **Python 3.11+**
- **`uv` package manager** (see [uv installation](https://github.com/astral-sh/uv))
- **Git**

### Development Setup

```bash
# Clone the repository
git clone https://github.com/manofthedown/open-inventory.git
cd open-inventory

# Create and activate virtual environment
uv sync

# Initialize database
uv run inventory init

# Run development server
uv run inventory run --reload
```

### Running Tests & Linting

```bash
# Run all tests
make test

# Run linter
make lint

# Run type checker
make types

# Run everything
make test && make lint && make types
```

## Development Workflow

1. **Create a feature branch** from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Write code** following the style and architecture guidelines below.

3. **Write tests** for new functionality. Aim for >80% coverage.

4. **Run checks locally**:
   ```bash
   make test
   make lint
   make types
   ```

5. **Commit with clear messages**:
   ```bash
   git commit -m "feat: add scan debounce logic"
   git commit -m "fix: handle negative stock validation"
   ```

6. **Push and open a pull request** against `develop`:
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Address feedback** from code review. Expect the GitHub Actions CI matrix to run on all commits.

## Code Style & Standards

### Python

- **Code formatter**: `ruff` (built-in to project)
- **Linter**: `ruff check`
- **Type checker**: `mypy`
- **Target**: Python 3.11+

Run `make lint` and `make types` before pushing.

### Architecture Principles

- **Modular**: Keep domain logic separate from transport/storage.
- **Testable**: Use dependency injection; avoid tight coupling.
- **Cross-platform**: Use `platformdirs` for filesystem paths. No shell-isms in hot code.
- **Offline-first**: Network calls are supplementary; fallback behavior must work.

### Module Structure

- `inv/core/` — Domain models (Pydantic), business logic, event signals
- `inv/storage/` — SQLAlchemy ORM, repositories, database initialization
- `inv/api/` — FastAPI routers and request/response handlers
- `inv/web/` — Jinja templates, HTMX partials, static assets
- `inv/lookup/` — Product data provider implementations (chain pattern)
- `inv/scan/` — Scanner input abstraction (HID, camera, etc.)

## Testing

- Unit tests in `tests/unit/`
- Integration tests in `tests/integration/` (using `TestClient`)
- Smoke tests in `tests/smoke/` (optional Playwright end-to-end)

Use `respx` for mocking external HTTP calls (provider lookups).

### Example Test

```python
import pytest
from fastapi.testclient import TestClient
from inv.main import create_app
from inv.settings import Settings

def test_scan_endpoint_creates_movement(settings: Settings):
    app = create_app(settings)
    client = TestClient(app)
    
    response = client.post(
        "/scan",
        json={"gtin": "5000112139107", "direction": "IN", "qty_multiplier": 1, "location_id": 1}
    )
    assert response.status_code == 200
```

## Milestones & Scope

This project follows a milestone-driven development plan (see `DEVELOPMENT_PLAN.md`):

- **M1**: Skeleton (core setup)
- **M2**: Scan loop (basic scanning)
- **M3**: Lookup chain (provider integration)
- **M4**: Casepacks & export
- **M5**: Packaging & cross-platform

**Out of scope for V1** (explicitly deferred to V2+):
- Lot/expiry tracking
- Camera/mobile scanning
- Multi-location transfers
- Authentication & user roles
- External webhooks
- Label printing
- Reporting dashboards

PRs should target the current active milestone unless they are bug fixes.

## Commit Message Format

Follow conventional commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Examples:
- `feat(scan): add autofocus on page load`
- `fix(storage): handle GTIN uniqueness constraint on upsert`
- `docs(quickstart): add Raspberry Pi setup guide`
- `test(lookup): add OFF provider timeout test`

## Pull Request Checklist

Before pushing, ensure:

- [ ] Tests pass: `make test`
- [ ] Linter passes: `make lint`
- [ ] Type checker passes: `make types`
- [ ] Code is cross-platform (no hardcoded paths, no Windows-only or Linux-only code)
- [ ] Documentation is updated if needed
- [ ] Commit messages are clear and follow conventions
- [ ] CI matrix passes on GitHub Actions (3 OSes × 2 Python versions)

## Questions?

Open a GitHub issue or discussion. We welcome feedback and questions!

---

**Thank you for contributing to open-inventory!** 🙏
