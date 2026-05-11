#!/usr/bin/env bash
# =============================================================================
# gen_docs.sh – Generate pytigon_lib API documentation with MkDocs + mkdocstrings
# =============================================================================
#
# Usage:
#   ./gen_docs.sh              # Build static HTML (output: site/)
#   ./gen_docs.sh serve        # Start live-reload dev server on port 8000
#   ./gen_docs.sh clean        # Remove built site/ directory
#   ./gen_docs.sh install      # Install all required dependencies
#   ./gen_docs.sh deploy       # Build and deploy to GitHub Pages (if configured)
#
# Prerequisites:
#   - Python 3.10+
#   - pip / pipx
#
# Output:
#   site/                      # Static HTML documentation (when built)
#
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The script is in pytigon_lib/; mkdocs.yml and docs/ are siblings of this script
# We run mkdocs from pytigon_lib/ so relative paths resolve correctly
MKDOCS_DIR="$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()  { echo -e "${CYAN}[STEP]${NC}  $*"; }

# ---------------------------------------------------------------------------
# install – Install Python dependencies
# ---------------------------------------------------------------------------
install_deps() {
    log_step "Installing MkDocs + Material theme + mkdocstrings..."

    # Check if pip is available
    if command -v pip3 &>/dev/null; then
        PIP="pip3"
    elif command -v pip &>/dev/null; then
        PIP="pip"
    else
        log_error "pip not found. Please install Python 3 and pip first."
        exit 1
    fi

    log_info "Using: $PIP"

    # Install core packages
    $PIP install --upgrade \
        mkdocs \
        mkdocs-material \
        mkdocstrings[python] \
        mkdocs-material-extensions \
        pymdown-extensions

    log_info "Installation complete."
    log_info "Installed packages:"
    $PIP show mkdocs mkdocs-material mkdocstrings 2>/dev/null | grep -E "^(Name|Version):"

    echo ""
    log_info "You can now run:  ./gen_docs.sh serve"
}

# ---------------------------------------------------------------------------
# check_deps – Verify that mkdocs is available
# ---------------------------------------------------------------------------
check_deps() {
    if ! command -v mkdocs &>/dev/null; then
        log_error "mkdocs not found. Run './gen_docs.sh install' first."
        exit 1
    fi
    if ! python3.13 -c "import mkdocstrings" 2>/dev/null; then
        log_error "mkdocstrings not found. Run './gen_docs.sh install' first."
        exit 1
    fi
    if ! python3.13 -c "import material" 2>/dev/null; then
        log_error "mkdocs-material not found. Run './gen_docs.sh install' first."
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# build – Generate static HTML in site/
# ---------------------------------------------------------------------------
build_docs() {
    check_deps
    log_step "Building static documentation..."

    local config_file="$MKDOCS_DIR/mkdocs.yml"

    if [[ ! -f "$config_file" ]]; then
        log_error "Configuration file not found: $config_file"
        exit 1
    fi

    cd "$MKDOCS_DIR"
    mkdocs build --config-file "$config_file" --clean

    local site_dir="$MKDOCS_DIR/site"
    if [[ -d "$site_dir" ]]; then
        log_info "Documentation built successfully!"
        log_info "Output directory: $site_dir"
        log_info "Open with: xdg-open $site_dir/index.html"
    else
        log_error "Build failed – site/ directory not created."
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# serve – Start live-reload development server
# ---------------------------------------------------------------------------
serve_docs() {
    check_deps
    log_step "Starting development server at http://127.0.0.1:8000 ..."

    local config_file="$MKDOCS_DIR/mkdocs.yml"

    if [[ ! -f "$config_file" ]]; then
        log_error "Configuration file not found: $config_file"
        exit 1
    fi

    cd "$MKDOCS_DIR"
    log_info "Watching for changes in: $MKDOCS_DIR/docs/"
    log_info "Press Ctrl+C to stop the server."
    echo ""
    mkdocs serve --config-file "$config_file" --dev-addr 127.0.0.1:8000
}

# ---------------------------------------------------------------------------
# clean – Remove built output
# ---------------------------------------------------------------------------
clean_docs() {
    local site_dir="$MKDOCS_DIR/site"
    if [[ -d "$site_dir" ]]; then
        log_step "Removing $site_dir ..."
        rm -rf "$site_dir"
        log_info "Cleaned."
    else
        log_info "Nothing to clean (site/ does not exist)."
    fi
}

# ---------------------------------------------------------------------------
# deploy – Build and push to GitHub Pages
# ---------------------------------------------------------------------------
deploy_docs() {
    check_deps
    log_step "Deploying to GitHub Pages..."

    local config_file="$MKDOCS_DIR/mkdocs.yml"

    if [[ ! -f "$config_file" ]]; then
        log_error "Configuration file not found: $config_file"
        exit 1
    fi

    cd "$MKDOCS_DIR"
    mkdocs gh-deploy --config-file "$config_file" --force

    log_info "Deployed to GitHub Pages."
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
case "${1:-build}" in
    install)
        install_deps
        ;;
    build)
        build_docs
        ;;
    serve)
        serve_docs
        ;;
    clean)
        clean_docs
        ;;
    deploy)
        deploy_docs
        ;;
    *)
        echo "Usage: $0 {build|serve|clean|install|deploy}"
        echo ""
        echo "  build     Generate static HTML documentation in site/"
        echo "  serve     Start live-reload development server on :8000"
        echo "  clean     Remove the built site/ directory"
        echo "  install   Install mkdocs + material + mkdocstrings"
        echo "  deploy    Build and deploy to GitHub Pages"
        echo ""
        echo "Default action: build"
        exit 1
        ;;
esac
