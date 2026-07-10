# pytigon-lib — Architecture

## Overview

pytigon-lib is the shared library layer for the Pytigon framework. It provides
Django extensions, HTML rendering, view generation, HTTP tools, and more.

## Module Map

```
pytigon_lib/
├── schtools/        # Core utilities (platform, crypto, env, JSON, LLVM)
├── schdjangoext/    # Django extensions (JSONModel, TreeModel, forms)
├── schhtml/         # HTML rendering engine (DC abstraction for PDF/DOCX/XLSX)
├── schviews/        # Generic Django CRUD views (GenericTable, permissions)
├── schparser/       # HTML and text parsers
├── schhttptools/    # HTTP/WebSocket client, OAuth2, REST
├── schindent/       # iHTML indentation preprocessor + markdown
├── schspreadsheet/  # ODF/OOXML spreadsheet processing
├── schtable/        # Server-side data table abstraction
├── schfs/           # Virtual filesystem (local + Django storage)
├── schtasks/        # Cron-like background task scheduler
├── schandroid/      # Android/Kivy integration
└── schtest/         # Testing utilities
```

## Key Design Patterns

### Device Context (DC) in schhtml

BaseDc in `basedc.py` defines an abstract drawing interface. Concrete subclasses:
- `PdfDc` — PDF output via fpdf2
- `DocxDc` — Word documents
- `XlsxDc` — Excel spreadsheets
- `CairoDc` — Cairo graphics
- `wxDc` — wxPython rendering

DC info classes in `dc_info.py` provide text measurement:
- `BaseDcInfo` — real measurements
- `NullDcinfo` — stubs for headless mode

### Generic Views in schviews

`GenericTable` generates URL patterns and registers views. Key classes:
- `GenericTable` — table configuration, URL pattern generation
- `GenericRows` — row-level view generation (list/detail/edit/add/delete)
- `VIEWS_REGISTER` — global dict of registered views by model

View mixins in `mixins.py` and `derived.py` provide reusable behavior across view types.

### JSON Model in schdjangoext

`JSONModel` allows dynamic fields stored as JSON within a text column, enabling
schema-free model extensions without migrations.
