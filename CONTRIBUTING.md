# Contributing to GroundGate

Thanks for helping make RAG answers verifiable. Issues describing real
production failure modes are as valuable as code.

## Development setup

```bash
git clone https://github.com/blpilla/groundgate
cd groundgate
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
pytest
```

The core has **zero runtime dependencies** — keep it that way. Anything that
needs a third-party package (provider SDKs, HTTP server) goes behind an
optional extra in `pyproject.toml`.

## What makes a good contribution

- **Failure cases first.** A new paired faithful/unfaithful case in
  `tests/data/insurance_pairs.json` or `benchmark/data/cases.json` that the
  current matcher gets wrong is the single most useful contribution.
  Anonymize anything from production.
- **Determinism where possible.** Prefer improving the deterministic matcher
  over widening the LLM-judge band; judge calls cost money and flicker.
- **The wire format is a contract.** `Verdict.to_dict()` shapes what the MCP
  server, CLI and HTTP consumers see — changes to it are breaking changes
  and need a version bump plus a CHANGELOG entry.

## Pull requests

- Run `pytest` — the suite must stay green on Python 3.10–3.12.
- If you touched matching/decomposition behavior, run
  `python benchmark/run.py` and commit the regenerated
  `benchmark/RESULTS.md`.
- Add or update tests for every behavior change; paired cases (faithful must
  pass, unfaithful must fail) are the house style.
- Update `CHANGELOG.md` under an `Unreleased` heading.

## Release process (maintainers)

1. Bump `version` in `pyproject.toml` and `__version__` in
   `groundgate/__init__.py` (keep them identical).
2. Move the `Unreleased` CHANGELOG section under the new version with today's
   date.
3. Commit, then tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. The `release.yml` workflow builds the sdist/wheel and publishes to PyPI
   via [trusted publishing](https://docs.pypi.org/trusted-publishers/) — no
   API tokens in the repo. First-time setup: register the GitHub repo as a
   trusted publisher for the `groundgate` project on PyPI.
5. Create the GitHub release from the tag, pasting the CHANGELOG section.

## Code style

Standard library only in the core, type hints everywhere, dataclasses for
data, tests named after the behavior they pin down. Comments explain
constraints, not mechanics.
