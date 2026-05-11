# Overview

## What is Pytigon?

Pytigon is a Python application framework that combines **wxPython** desktop GUI
capabilities with **Django** web framework patterns. The `pytigon_lib` package
provides the core library with 13 specialized modules.

## Supported Platforms

| Platform | Status |
|----------|--------|
| Linux | :material-check: Full support |
| Windows | :material-check: Full support |
| Android | :material-check: Kivy-based |
| Emscripten (Web) | :material-check: Experimental |

## Architecture

```
pytigon_lib/
├── schtools/         # Core utilities, paths, platform detection
├── schdjangoext/     # Django models, forms, GraphQL, REST
├── schhtml/          # HTML → PDF/DOCX/XLSX rendering engine
├── schhttptools/     # HTTP client, WebSocket, ASGI bridge
├── schtable/         # Abstract table/data exchange interface
├── schparser/        # HTML/XML parsing (lxml)
├── schspreadsheet/   # OOXML/ODF processing
├── schfs/            # Virtual file system, ZIP, file ops
├── schtasks/         # Twisted-based task scheduler
├── schandroid/       # Android/Kivy integration
├── schtest/          # Testing utilities
├── schindent/        # Code formatting, Py→JS conversion
└── schviews/         # Generic Django CRUD views
```

## Key Design Principles

### Device Context (DC) Pattern

All document rendering uses an abstract "device context" that decouples layout
from output format:

| DC Class | Output Format |
|----------|---------------|
| `PdfDc` | PDF documents |
| `DocxDc` | DOCX documents |
| `XlsxDc` | XLSX spreadsheets |
| `CairoDc` | Cairo graphics |
| `NullDc` | Dimension calculation only |

### Table Interface

The abstract [`Table`](../api/schtable.md) class defines a uniform protocol for
server-side data access with 7 standard commands (`CMD_INFO`, `CMD_PAGE`,
`CMD_COUNT`, `CMD_SYNC`, `CMD_AUTO`, `CMD_EXEC`, `CMD_RECASSTR`).

### Generic Views

[`GenericTable`](../api/schviews.md) and [`GenericRows`](../api/schviews.md) auto-generate
Django URL patterns for full CRUD operations on any model.

## Dependencies

- **Core:** Python 3.10+, lxml
- **Django extensions:** Django 4.x+
- **HTTP:** httpx, Django Channels
- **PDF:** reportlab, cairo
- **Task scheduling:** Twisted
- **Android:** Kivy, android.permissions
