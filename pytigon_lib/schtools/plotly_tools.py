import asyncio
import tempfile
import os

from playwright.async_api import async_playwright


async def make_chart(fig):
    """
    Generate a PNG image of a Plotly figure by rendering it in a headless browser.

    Args:
        fig (plotly.graph_objs._figure.Figure): The Plotly figure to be saved as a PNG file.

    Returns:
        str: The file path of the generated PNG image.
    """

    html_file_name = tempfile.NamedTemporaryFile(suffix=".html").name
    png_file_name = tempfile.NamedTemporaryFile(suffix=".png").name
    fig.write_html(html_file_name)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("file://" + html_file_name)
        await page.screenshot(path=png_file_name, full_page=True)
    os.unlink(html_file_name)
    return png_file_name


def sync_make_chart(fig):
    """
    Synchronous version of :func:`make_chart`. This function blocks until the task is complete.

    Args:
        fig (plotly.graph_objs._figure.Figure): The Plotly figure to be saved as a PNG file.

    Returns:
        str: The file path of the generated PNG image.
    """

    return asyncio.run(make_chart(fig))


if __name__ == "__main__":
    import plotly.express as px

    fig = px.scatter(x=range(10), y=range(10))
    png_file_name = sync_make_chart(fig)
    # process
    os.unlink(png_file_name)
