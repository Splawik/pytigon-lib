"""Common utilities for schspreadsheet package."""


def transform_str(s):
    """Replace special character sequences in template strings.

    '***' -> double quote, '**' -> single quote.
    """
    return s.replace("***", '"').replace("**", "'")
