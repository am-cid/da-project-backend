import io
from typing import Any

import polars as pl


def read_csv(file_contents: bytes) -> list[dict[str, Any]]:
    """Reads csv from uploaded file and returns list of rows as dicts"""
    df = pl.read_csv(io.BytesIO(file_contents))
    return df.to_dicts()
