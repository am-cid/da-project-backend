from io import StringIO
from typing import Literal

import polars as pl
import polars.datatypes as dtype
from app.types import ColumnDataType

BOOLEAN_TRUE_VALUES = {"true", "yes", "y", "on"}
BOOLEAN_FALSE_VALUES = {"false", "no", "n", "off"}


def clean_csv(
    file_contents: str,
    strategy: Literal["forward", "backward", "min", "max", "mean", "zero", "one"],
) -> tuple[str, list[str], list[str], list[ColumnDataType]]:
    """Returns:
    - cleaned csv string
    - cleaned csv labels
    - cleaned csv rows as comma separated string
    - cleaned csv dtype
    """
    df = pl.read_csv(
        StringIO(
            remove_comma_inside_quotes(file_contents),
        ),
    ).fill_null(strategy=strategy)
    labels = []
    rows = []
    dtypes: list[ColumnDataType] = []
    for col in df.get_columns():
        col_name = col.name.strip()
        df = df.with_columns(
            col.cast(dtype.String).str.to_lowercase().str.strip_chars().alias(col_name),
        )
        og_dtype = col.dtype
        col = df.get_column(col_name)
        match og_dtype:
            case dtype.String | dtype.Categorical | dtype.Enum | dtype.Utf8:
                string_vals = col.to_list()
                if possibly_bool_column(string_vals):
                    df = df.with_columns(col.is_in(BOOLEAN_TRUE_VALUES).alias(col_name))
                    dtypes.append(ColumnDataType.BOOLEAN)
                else:
                    dtypes.append(ColumnDataType.STRING)
            case dtype.Boolean:
                dtypes.append(ColumnDataType.BOOLEAN)
            case (
                dtype.Decimal
                | dtype.Float32
                | dtype.Float64
                | dtype.Int8
                | dtype.Int16
                | dtype.Int32
                | dtype.Int64
                | dtype.UInt8
                | dtype.UInt16
                | dtype.UInt32
                | dtype.UInt64
            ):
                dtypes.append(ColumnDataType.NUMBER)
        col = df.get_column(col_name)
        labels.append(col_name)
        rows.append(",".join(col.cast(dtype.String).to_list()))
    return df.write_csv(), labels, rows, dtypes


def remove_comma_inside_quotes(file_contents: str) -> str:
    "removes commas inside either single or double quotes in a csv file"
    quote_char: str | None = None
    output: list[str] = []
    for char in file_contents:
        if char in ['"', "'"]:
            if quote_char is None:
                quote_char = char
            elif quote_char == char:
                quote_char = None
        elif char == "," and quote_char:
            continue
        output.append(char)
    return "".join(output)


def possibly_bool_column(string_vals: list[str]) -> bool:
    true_count = sum(1 for x in string_vals if x in BOOLEAN_TRUE_VALUES)
    false_count = sum(1 for x in string_vals if x in BOOLEAN_FALSE_VALUES)
    total_count = len(string_vals)
    return true_count + false_count > total_count * 0.8
