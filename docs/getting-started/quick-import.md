# Quick Import Reference

## Initialization

```python
from pytigon_lib import init_paths
init_paths('myproject')
```

## Core Utilities

```python
from pytigon_lib.schtools.main_paths import get_main_paths
from pytigon_lib.schtools.platform_info import platform_name
from pytigon_lib.schtools.tools import bencode, bdecode, norm_indent
```

## Django Extensions

```python
from pytigon_lib.schdjangoext.models import JSONModel, TreeModel, AssociatedModel
from pytigon_lib.schdjangoext.fields import (
    ManyToManyField, ManyToManyFieldWithIcon, NullBooleanField
)
from pytigon_lib.schdjangoext.fastform import form_from_str
```

## Document Rendering

```python
from pytigon_lib.schhtml.basedc import BaseDc, NullDc, SubDc
from pytigon_lib.schhtml.pdfdc import PdfDc, PdfDcInfo
from pytigon_lib.schhtml.docxdc import DocxDc, DocxDcinfo
from pytigon_lib.schhtml.xlsxdc import XlsxDc, XlsxDcinfo
from pytigon_lib.schhtml.htmlviewer import HtmlViewerParser, stream_from_html
```

## HTTP Client

```python
from pytigon_lib.schhttptools.httpclient import HttpClient, RetHttp, AppHttp
from pytigon_lib.schhttptools.rest_client import get_rest_client
```

## Table Interface

```python
from pytigon_lib.schtable.table import Table, CMD_INFO, CMD_PAGE, CMD_COUNT
from pytigon_lib.schtable.dbtable import DbTable
```

## Parsing

```python
from pytigon_lib.schparser.parser import Parser, Elem
from pytigon_lib.schparser.html_parsers import (
    SimpleTabParser, TreeParser, ShtmlParser
)
```

## Spreadsheets

```python
from pytigon_lib.schspreadsheet.ooxml_process import OOXmlDocTransform
from pytigon_lib.schspreadsheet.odf_process import OdfDocTransform
```

## File System

```python
from pytigon_lib.schfs.vfstools import (
    open_file, get_unique_filename, norm_path, extractall
)
```

## Task Scheduling

```python
from pytigon_lib.schtasks.schschedule import SChScheduler
```

## Generic Views

```python
from pytigon_lib.schviews import (
    GenericTable, GenericRows, make_path, gen_tab_action, gen_row_action,
    VIEWS_REGISTER, extend_generic_view
)
from pytigon_lib.schviews.viewtools import (
    ExtTemplateResponse, render_to_response_ext
)
from pytigon_lib.schviews.actions import (
    ok_response, cancel_response, error_response
)
```
