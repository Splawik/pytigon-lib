"""Render Plotly figures to PNG using a headless browser.

``playwright`` is an optional dependency: it is imported lazily so that
importing this module (and therefore the rest of :mod:`pytigon_lib.schtools`)
does not fail on installations that do not need chart rendering.
"""

import asyncio
import os
import tempfile

#: Default seconds allowed for the whole browser render.
DEFAULT_TIMEOUT = 30.0


def _playwright():
    """Import and return ``playwright.async_api.async_playwright``.

    Raises:
        ImportError: If Playwright is not installed.
    """
    from playwright.async_api import async_playwright

    return async_playwright


async def make_chart(fig, timeout=DEFAULT_TIMEOUT):
    """
    Generate a PNG image of a Plotly figure by rendering it in a headless browser.

    The intermediate HTML file and the browser instance are always cleaned up,
    including when the render times out or raises.

    Args:
        fig (plotly.graph_objs._figure.Figure): The Plotly figure to be saved as a PNG file.
        timeout: Seconds allowed for the whole render.

    Returns:
        str: The file path of the generated PNG image.
    """
    async_playwright = _playwright()

    html_file_name = tempfile.NamedTemporaryFile(
        suffix=".html", delete=False
    ).name
    png_file_name = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
    try:
        fig.write_html(html_file_name)

        async with asyncio.timeout(timeout):
            async with async_playwright() as p:
                async with await p.chromium.launch() as browser:
                    page = await browser.new_page()
                    await page.goto("file://" + html_file_name)
                    await page.screenshot(path=png_file_name, full_page=True)
    except BaseException:
        for name in (html_file_name, png_file_name):
            try:
                os.unlink(name)
            except OSError:
                pass
        raise
    os.unlink(html_file_name)
    return png_file_name


def sync_make_chart(fig, timeout=DEFAULT_TIMEOUT):
    """
    Synchronous version of :func:`make_chart`. This function blocks until the task is complete.

    Args:
        fig (plotly.graph_objs._figure.Figure): The Plotly figure to be saved as a PNG file.
        timeout: Seconds allowed for the whole render.

    Returns:
        str: The file path of the generated PNG image.

    Raises:
        RuntimeError: If called from inside a running event loop. Use
            :func:`make_chart` and await it instead.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        raise RuntimeError(
            "sync_make_chart() cannot be called from a running event loop; "
            "await make_chart() instead."
        )
    return asyncio.run(make_chart(fig, timeout))


if __name__ == "__main__":
    import plotly.express as px

    fig = px.scatter(x=range(10), y=range(10))
    png_file_name = sync_make_chart(fig)
    # process
    os.unlink(png_file_name)
