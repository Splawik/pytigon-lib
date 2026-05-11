# How to Use the Pytigon Documentation System

This guide explains how to generate, serve, and maintain API documentation
for `pytigon_lib` using **MkDocs** with the **Material for MkDocs** theme
and **mkdocstrings** for automatic Python docstring extraction.

---

## Quick Start (TL;DR)

```bash
# 1. Enter the pytigon_lib directory
cd pytigon_lib

# 2. Install dependencies (one-time)
./gen_docs.sh install

# 3. Start live-reload preview server
./gen_docs.sh serve

# 4. Open http://127.0.0.1:8000 in your browser

# 5. When ready, build static HTML
./gen_docs.sh build
# Output is in: pytigon_lib/site/
```

---

## File Structure

```
pytigon_lib/
├── mkdocs.yml                    # MkDocs configuration (theme, plugins, nav)
├── gen_docs.sh                   # Bash script for all operations
├── docs/                         # Documentation source (Markdown)
│   ├── index.md                  # Landing page
│   ├── HOWTO.md                  # This file
│   ├── getting-started/
│   │   ├── overview.md           # Architecture overview
│   │   └── quick-import.md       # Import cheat sheet
│   └── api/                      # API reference (auto-generated from docstrings)
│       ├── schtools.md
│       ├── schdjangoext.md
│       ├── schhtml.md
│       ├── schhttptools.md
│       ├── schtable.md
│       ├── schparser.md
│       ├── schspreadsheet.md
│       ├── schfs.md
│       ├── schtasks.md
│       ├── schandroid.md
│       ├── schtest.md
│       ├── schindent.md
│       └── schviews.md
└── site/                         # Built output (generated, git-ignored)
```

---

## `gen_docs.sh` Commands

| Command | Description |
|---------|-------------|
| `./gen_docs.sh install` | Install all Python dependencies (mkdocs, material, mkdocstrings) |
| `./gen_docs.sh build` | Generate static HTML in `site/` |
| `./gen_docs.sh serve` | Start live-reload development server on port 8000 |
| `./gen_docs.sh clean` | Remove `site/` directory |
| `./gen_docs.sh deploy` | Build and deploy to GitHub Pages |

---

## How mkdocstrings Works

The API reference pages use the `::: module.path` syntax provided by mkdocstrings.
For example, [`docs/api/schtools.md`](api/schtools.md) contains:

```markdown
# schtools – Core Tools and Platform Management

::: pytigon_lib.schtools
    options:
      show_submodules: true
      members: true
```

This tells mkdocstrings to:

1. Import `pytigon_lib.schtools`
2. Extract all docstrings from that module and its submodules
3. Render them as API documentation with signatures, parameter tables, and source code

The docstring style detected is **Google-style** (as configured in [`mkdocs.yml`](../mkdocs.yml)):

```python
def init_paths(prj_name=None, env_path=None):
    """Initialize system paths based on the project name and environment path.

    Args:
        prj_name (str, optional): The name of the project. Defaults to None.
        env_path (str, optional): Path to the environment configuration. Defaults to None.
    """
```

---

## Adding Documentation for a New Module

To add documentation for a new module (e.g., `schnew`):

**Step 1:** Create the API reference file:

```bash
cat > pytigon_lib/docs/api/schnew.md << 'EOF'
# schnew – Description of the new module

::: pytigon_lib.schnew
    options:
      show_submodules: true
      members: true
EOF
```

**Step 2:** Add the page to [`mkdocs.yml`](../mkdocs.yml) under the `nav.api` section:

```yaml
nav:
  - API Reference:
      - schtools: api/schtools.md
      # ...existing entries...
      - schnew: api/schnew.md     # <-- add this line
```

**Step 3:** Rebuild or restart the dev server:

```bash
./gen_docs.sh build   # or ./gen_docs.sh serve
```

---

## Writing Good Docstrings

mkdocstrings renders your Python docstrings. Follow these guidelines for
the best output:

```python
def my_function(param1: str, param2: int = 42) -> bool:
    """Short description of what the function does.

    Longer explanation can go here, spanning multiple paragraphs.
    Include usage examples, edge cases, and design rationale.

    Args:
        param1: Description of the first parameter.
        param2: Description of the second parameter. Defaults to 42.

    Returns:
        True if the operation succeeded, False otherwise.

    Raises:
        ValueError: If param1 is empty.
        IOError: If a file operation fails.

    Example:
        >>> my_function("hello", 10)
        True
    """
```

Key points:

- Use **Google-style** docstrings (`Args:`, `Returns:`, `Raises:`)
- Add type annotations – they appear in signatures automatically
- Include `Example:` sections for complex functions
- Document class `__init__` parameters in the class docstring

---

## Customizing the Theme

Edit [`mkdocs.yml`](../mkdocs.yml) to change:

- **Color scheme**: Modify the `theme.palette` entries
- **Navigation**: Add, remove, or reorder entries under `nav`
- **Features**: Toggle Material features under `theme.features`
- **mkdocstrings options**: Control what appears in API docs

Common mkdocstrings options for individual pages:

```yaml
options:
  show_source: false        # Hide source code
  inherited_members: true   # Show inherited methods
  members_order: source     # Order by source file position
  filters: ["!^_"]          # Exclude private members
```

---

## Continuous Integration

Add to your CI pipeline (`.github/workflows/docs.yml`):

```yaml
name: Build Docs
on:
  push:
    branches: [main]
jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install mkdocs mkdocs-material mkdocstrings[python]
      - run: cd pytigon_lib && mkdocs build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: pytigon_lib/site/
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `mkdocs: command not found` | Run `./gen_docs.sh install` |
| `ModuleNotFoundError: pytigon_lib` | Run mkdocs from `pytigon_lib/` directory (the script does this automatically) |
| Import errors in mkdocstrings | Ensure the module's dependencies are installed in the same Python environment |
| Build is very slow | Add `--no-directory-urls` or use `--dirty` for incremental builds during development |
| Material theme features missing | Make sure `mkdocs-material` and `pymdown-extensions` are installed |
