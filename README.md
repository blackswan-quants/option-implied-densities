# option-implied-densities

Investigates whether pre-release option-implied probability densities can predict the size of price moves around macroeconomic news events.

**Research question.** Does the option-implied density before FOMC, CPI and payrolls releases predict the size of the move, and are realised moves calibrated to it?

BlackSwan Quants research project P4, 2026/27.

| Role | Name |
| --- | --- |
| Lead | Patrizio Mandelli |
| Members | Francesco Nicolò, Kamil Rebeiz |

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/blackswan-quants/option-implied-densities.git
cd option-implied-densities
uv sync                      # creates .venv with Python 3.12 and all dependencies
uv run pre-commit install    # runs ruff and mypy on every commit
cp .env.example .env         # then fill in your own values
```

Check that everything works:

```bash
uv run pytest
```

## Repository layout

```
src/oid/
    config.py       settings from .env, logging setup
    data/           download and cleaning of option chains and prices
    events/         FOMC, CPI and payrolls calendar
    density/        risk-neutral density extraction and checks
    evaluation/     forecast and calibration tests
tests/              pytest tests, mirroring src/oid/
notebooks/          exploration only, no logic that other code depends on
reports/            monthly notes and final report (club template)
data/               local data, not committed (see OID_DATA_DIR in .env)
```

## Workflow

1. Every task is a GitHub issue, agreed at the weekly call.
2. Work on a branch from an up-to-date `main`: `feat/...`, `fix/...`, `docs/...`, `refactor/...`.
3. Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/): `feat: add SVI fit`, `fix: handle zero bids`.
4. Open a pull request using the template. `main` is protected: every PR needs CI to pass and one approval.
5. Peer review in the team, then the lead check, then squash merge.

## Conventions

- Python 3.12, dependencies managed with uv and pinned in `uv.lock`. Add packages with `uv add <pkg>` (or `uv add --dev <pkg>`), never with pip.
- PEP 8 via ruff, full type hints checked by mypy in strict mode, NumPy style docstrings.
- Every numeric output is covered by a test or an assertion. Financial invariants (non-negative densities, unit mass, no-arbitrage bounds) are `assert`s, not comments.
- Pricing and signal functions take an explicit `as_of` date. Never use an implicit "today".
- Use `logging`, not `print`.
- Secrets live in `.env`. Data stays out of git.
- Maths is checked by someone other than its author before it goes into a report.
