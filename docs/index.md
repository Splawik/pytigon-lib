# Pytigon Library

**Version:** 0.260511 · **License:** LGPL 3.0 · **Author:** Sławomir Chołaj

---

## Overview

Pytigon is a Python library providing a comprehensive framework for building
web applications with Django, supporting multiple platforms (Windows, Linux,
Android, Emscripten). It extends Django with additional functionality for HTML
generation, HTTP tools, spreadsheet processing, and more.

## Module Map

| Module | Purpose |
|--------|---------|
| [`schtools`](api/schtools.md) | Platform detection, path management, environment, utilities |
| [`schdjangoext`](api/schdjangoext.md) | Django models, forms, fields, GraphQL, REST |
| [`schhtml`](api/schhtml.md) | HTML generation, PDF/DOCX/XLSX rendering |
| [`schhttptools`](api/schhttptools.md) | HTTP client, REST, WebSocket, ASGI bridge |
| [`schtable`](api/schtable.md) | Server-side table/data interface |
| [`schparser`](api/schparser.md) | HTML and text parsing utilities |
| [`schspreadsheet`](api/schspreadsheet.md) | OOXML/ODF spreadsheet processing |
| [`schfs`](api/schfs.md) | Virtual file system and file operations |
| [`schtasks`](api/schtasks.md) | Background task scheduling |
| [`schandroid`](api/schandroid.md) | Android platform integration (Kivy) |
| [`schtest`](api/schtest.md) | Testing utilities |
| [`schindent`](api/schindent.md) | Code indentation and formatting |
| [`schviews`](api/schviews.md) | Generic Django views with CRUD support |

## Quick Start

```python
from pytigon_lib import init_paths
init_paths('myproject')

from pytigon_lib.schtools.main_paths import get_main_paths
from pytigon_lib.schdjangoext.models import JSONModel, TreeModel
from pytigon_lib.schhtml.basedc import PdfDc, DocxDc, XlsxDc
from pytigon_lib.schhttptools.httpclient import HttpClient
from pytigon_lib.schtable.table import Table
from pytigon_lib.schviews.viewtools import render_to_response_ext
```

## Key Design Patterns

- **Device Context (DC)** – abstract rendering backend (PDF, DOCX, XLSX, Cairo)
- **Table Interface** – uniform client-server data exchange through abstract `Table`
- **Generic Views** – `GenericTable`/`GenericRows` for automatic CRUD URL patterns
- **Platform Abstraction** – isolated platform code in `schtools.platform_info`
