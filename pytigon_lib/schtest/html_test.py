"""
This module provides functions to extract the content of the HTML body tag from HTML content
and to compare the content of two HTML files, excluding the HTML tags outside of the <body> tag.

Functions:
    extract_body_content(html_content):
        Extracts the content of the HTML body tag from the given HTML content.

    html_content_cmp(file_path1, file_path2):
"""


def extract_body_content(html_content):
    """
    Extract the content of the HTML body tag from the given HTML content.

    If the "<body>" tag is present in the HTML content, this function returns the content
    between the "<body>" and "</body>" tags. Otherwise, it returns the original HTML content.

    Args:
        html_content (str): The HTML content to extract the body content from.

    Returns:
        str: The content of the HTML body tag.
    """
    if "<body>" in html_content:
        return html_content.split("<body>")[1].split("</body>")[0]
    return html_content


def html_content_cmp(file_path1, file_path2):
    """
    Compares the content of two HTML files, excluding the HTML tags outside of the <body> tag.

    Args:
        file_path1 (str): The path of the first file.
        file_path2 (str): The path of the second file.

    Returns:
        bool: True if the content of the two files is the same, False otherwise.
    """
    with (
        open(file_path1, "rt") as f1,
        open(file_path2, "rt") as f2,
    ):
        content1 = extract_body_content(f1.read())
        content2 = extract_body_content(f2.read())
        return content1 == content2
