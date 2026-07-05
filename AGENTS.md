# AGENTS.md - pytigon-lib

## Build & Development Commands

```bash
ruff check .                          # Lint all code
ruff format --check .                 # Check formatting
ruff format .                         # Auto-format code
python -m pytest tests/               # Run test suite
```

## Project Overview

**pytigon-lib** is a Python/Django full-stack application framework licensed under LGPL-3.0. Requires Python >= 3.12, Django >= 6.0.

### Key Architecture

13 submodules under `pytigon_lib/`:

| Module | Purpose |
|--------|---------|
| `schtools` | Core utilities: platform detection, encryption, LLVM, Plotly, IMAP |
| `schdjangoext` | Django extensions: JSONModel, TreeModel, GraphQL, OAuth, forms |
| `schhtml` | HTML rendering engine: Device Context (DC) abstraction for PDF/DOCX/XLSX/Cairo |
| `schhttptools` | HTTP/WebSocket: REST client, ASGI bridge, OAuth2 |
| `schviews` | Generic Django CRUD views (GenericTable, permissions with django-rules) |
| `schindent` | Indentation-based ihtml preprocessor + markdown integration |
| `schspreadsheet` | ODF/OOXML spreadsheet processing |
| `schparser` | HTML and text parsing |
| `schtable` | Server-side data table abstraction |
| `schfs` | Virtual filesystem (local + Django storage) |
| `schtasks` | Cron-like background task scheduler |
| `schandroid` | Android/Kivy integration |
| `schtest` | Testing utilities |

### Code Conventions

- **Python 3.12+** with modern type annotations (`list[str]` not `List[str]`)
- Line length: 120 characters (ruff config)
- LF line endings
- Import sorting via ruff (I rule)
- Tests mirror `pytigon_lib/` module structure under `tests/`
- Test imports use bare names from project root (not relative imports)

### Ruff Lint Configuration

- Rules: E, W, F, I, UP, SIM, RUF
- Ignored: SIM102, SIM105, SIM108, SIM115, SIM116, SIM117, SIM118, RUF002, RUF003, RUF005, RUF012, RUF059
- Per-file ignores defined in `pyproject.toml`

### Versioning

Date-based: `0.YYMMDD` (e.g. `0.260705` = July 5, 2026). Version is defined in both `pyproject.toml` and `pytigon_lib/__init__.py` — keep them in sync.

### Dependencies

Core: Django>=6.0, lxml, httpx, fpdf2, Pillow, python-docx, htmldocx, xlsxwriter, openpyxl, markdown, pyquery, autobahn, pyexcel, llvmlite, plotly, numpy, pscript, svglib, cryptography, fs, rules, python-dateutil, django-environ

Dev: ruff>=0.3, pytest>=7.0, pytest-django>=4.5
