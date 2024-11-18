from io import StringIO

import polars as pl
import polars.datatypes as dtype
from app.types import ColumnDataType

BOOLEAN_TRUE_VALUES = {"true", "yes", "y", "on"}
BOOLEAN_FALSE_VALUES = {"false", "no", "n", "off"}


def clean_csv(
    file_contents: str,
) -> tuple[str, list[str], list[str], list[ColumnDataType]]:
    """Returns:
    - cleaned csv string
    - cleaned csv labels
    - cleaned csv rows as comma separated string
    - cleaned csv dtype
    """
    df = pl.read_csv(StringIO(file_contents))
    labels = []
    rows = []
    dtypes: list[ColumnDataType] = []
    for col in df.get_columns():
        df = df.with_columns(
            col.cast(dtype.String).str.to_lowercase().str.strip_chars().alias(col.name),
        )
        og_dtype = col.dtype
        col = df.get_column(col.name)
        match og_dtype:
            case dtype.String | dtype.Categorical | dtype.Enum | dtype.Utf8:
                string_vals = col.to_list()
                true_count = sum(1 for x in string_vals if x in BOOLEAN_TRUE_VALUES)
                false_count = sum(1 for x in string_vals if x in BOOLEAN_FALSE_VALUES)
                total_count = len(string_vals)
                possibly_bool_column = true_count + false_count > total_count * 0.8
                if possibly_bool_column:
                    df = df.with_columns(col.is_in(BOOLEAN_TRUE_VALUES).alias(col.name))
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
        col = df.get_column(col.name)
        labels.append(col.name)
        rows.append(",".join(col.cast(dtype.String).to_list()))
    return df.write_csv(), labels, rows, dtypes
