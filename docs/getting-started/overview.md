# Overview

## What is Pytigon?

Pytigon is a full-stack Python/Django application framework. The `pytigon_lib`
package provides the core library with 13 specialized modules.

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
├── schhtml/          # HTML -> PDF/DOCX/XLSX rendering engine
├── schhttptools/     # HTTP client, WebSocket, ASGI bridge
├── schtable/         # Abstract table/data exchange interface
├── schparser/        # HTML and text parsing
├── schspreadsheet/   # OOXML/ODF processing
├── schfs/            # Virtual file system, file ops
├── schtasks/         # Background task scheduler
├── schandroid/       # Android/Kivy integration
├── schtest/          # Testing utilities
├── schindent/        # iHTML preprocessor + markdown integration
└── schviews/         # Generic Django CRUD views
```

## Key Design Principles

### Device Context (DC) Pattern

All document rendering uses an abstract "device context" that decouples layout
from output format:

| DC Class | Module | Output Format |
|----------|--------|---------------|
| `PdfDc` | `schhtml.pdfdc` | PDF documents |
| `DocxDc` | `schhtml.docxdc` | DOCX documents |
| `XlsxDc` | `schhtml.xlsxdc` | XLSX spreadsheets |
| `BaseDc` | `schhtml.basedc` | Abstract base class |
| `NullDc` | `schhtml.basedc` | Dimension calculation only |

### Table Interface

The abstract [`Table`](../api/schtable.md) class defines a uniform protocol for
server-side data access with 7 standard commands (`CMD_INFO`, `CMD_PAGE`,
`CMD_COUNT`, `CMD_SYNC`, `CMD_AUTO`, `CMD_EXEC`, `CMD_RECASSTR`).

### Generic Views

[`GenericTable`](../api/schviews.md) and [`GenericRows`](../api/schviews.md) auto-generate
Django views for full CRUD operations on any model. Views are registered in the
`VIEWS_REGISTER` dictionary.

## Dependencies

- **Core:** Python 3.12+, lxml
- **Django extensions:** Django >= 6.0
- **HTTP:** httpx
- **PDF:** fpdf2
- **Task scheduling:** autobahn
- **Android:** Kivy
