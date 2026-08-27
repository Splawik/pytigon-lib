"""Environment tweaks improving embedded WebKitGTK stability.

Used by Pytigon GUI before the first WebView is created. Everything is
applied with ``setdefault`` so a user can still override the values.
"""

import os


def enable_webkit_stability_env():
    """Set environment variables making WebKitGTK stable as an embedder."""
    # Escape hatch for debugging/reproducing stock behaviour.
    if os.environ.get("PYTIGON_SKIP_WEBKIT_ENV"):
        return

    # Known renderer crashes on some drivers/compositors
    os.environ.setdefault("WEBKIT_DISABLE_DMABUF_RENDERER", "1")
    os.environ.setdefault("WEBKIT_DISABLE_COMPOSITING_MODE", "1")

    # Force pure-software GTK drawing stack - the GPU paths are the
    # most common source of intermittent crashes/flicker for embedded
    # WebKit (GTK 3GL fallbacks, EGL faults in the UI process).
    os.environ.setdefault("GSK_RENDERER", "cairo")
    os.environ.setdefault("GDK_GL", "disable")

    # Since WebKitGTK 2.40 the bwrap sandbox fails on systems with AppArmor
    # user namespace restrictions (Ubuntu 24.04+) and since 2.44 the old
    # WEBKIT_FORCE_SANDBOX variable no longer allows disabling it - the
    # NetworkProcess crashes and nothing loads ("networkProcessCrashed").
    os.environ.setdefault("WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS", "1")

    # High ASLR entropy (vm.mmap_rnd_bits >= 30, the new default on
    # Ubuntu 24.04+) collides with fixed-address JIT mappings and causes
    # random segmentation faults inside JavaScriptCore at startup.
    jit_ok = False
    try:
        with open("/proc/sys/vm/mmap_rnd_bits", encoding="ascii") as f:
            jit_ok = int(f.read().strip()) < 30
    except (OSError, ValueError):
        # Cannot check (e.g. restricted /proc): play it safe.
        pass
    if not jit_ok:
        os.environ.setdefault("JSC_useJIT", "false")
        os.environ.setdefault("JSC_useRegExpJIT", "false")
