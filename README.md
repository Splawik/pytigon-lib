# pytigon-lib

**Pytigon** is a full-stack Python/Django application framework designed for building web applications across multiple environments: desktop, web server, Android, and WebAssembly (Emscripten).

This library (`pytigon-lib`) is the core component of the Pytigon platform, providing:

- **Multi-format document rendering** — Convert HTML to PDF, DOCX, XLSX, and Cairo graphics
- **Indentation-based HTML preprocessor (ihtml)** — Write templates in a concise, Python-like indented syntax
- **Django extensions** — Auto-generated CRUD views, GraphQL integration, custom model/form fields
- **Spreadsheet processing** — Transform ODF (.ods) and OOXML (.xlsx) spreadsheets
- **Virtual filesystem** — Unified API for local and Django storage backends
- **Task scheduling** — Background task scheduling with cron-like patterns
- **HTTP/WebSocket tools** — REST clients, ASGI bridges, OAuth2 helpers

## Installation

```bash
pip install pytigon-lib
```

With optional dependencies:

```bash
pip install pytigon-lib[spreadsheet,llvm,plotting,svg]
```

## Quick start

### Render HTML to PDF

```python
from pytigon_lib.schhtml.main import html_to_pdf

html_content = "<html><body><h1>Hello World</h1></body></html>"
with open("output.pdf", "wb") as f:
    f.write(html_to_pdf(html_content))
```

### Auto-generate Django CRUD views

```python
from pytigon_lib.schviews import GenericTable

GenericTable(MyModel).register()
```

## Requirements

- Python 3.8+
- Django >= 6

## License

LGPLv3 — see [LICENSE](LICENSE)
