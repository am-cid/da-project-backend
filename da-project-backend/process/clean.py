from collections import Counter
from difflib import SequenceMatcher
from io import StringIO
from typing import Literal

import polars as pl
import polars.datatypes as dtype
from app.types import ColumnDataType, CurrencySymbol
from polars.series import Series

BOOLEAN_TRUE_VALUES = {
    "true",
    "yes",
    "y",
    "on",
    "t",
    "yeah",
    "yep",
    "ye",
    "ok",
    "okay",
    "affirmative",
    "certainly",
    "positive",
}
BOOLEAN_FALSE_VALUES = {
    "false",
    "no",
    "n",
    "off",
    "f",
    "nah",
    "na",
    "nop",
    "nope",
    "negative",
    "absent",
    "none",
}
GENDER_MALE_VALUES = {
    "male",
    "m",
    "man",
    "boy",
    "gentleman",
    "masculine",
    "he",
    "his",
    "him",
    "guy",
    "dude",
    "bro",
    "sir",
    "king",
}
GENDER_FEMALE_VALUES = {
    "female",
    "f",
    "woman",
    "girl",
    "lady",
    "feminine",
    "she",
    "her",
    "hers",
    "gal",
    "chick",
    "miss",
    "madam",
    "ma'am",
    "queen",
}
COUNT_THRESHOLD = 0.8
SIMILARITY_THRESHOLD = 0.8


def clean_csv(
    file_contents: str,
    strategy: Literal["forward", "backward", "min", "max", "mean", "zero", "one"],
) -> tuple[
    str, list[str], list[str], list[ColumnDataType], list[CurrencySymbol | None]
]:
    """Returns:
    - cleaned csv string
    - cleaned csv labels
    - cleaned csv rows as comma separated string
    - cleaned csv dtype
    - cleaned csv currency symbols (if any)
    """
    df = pl.read_csv(
        StringIO(
            remove_comma_inside_quotes(file_contents),
        ),
    ).fill_null(strategy=strategy)
    labels = []
    rows = []
    dtypes: list[ColumnDataType] = []
    currencies: list[CurrencySymbol | None] = []
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
                    currencies.append(None)
                elif res := possibly_currency_column(string_vals):
                    df = df.with_columns(
                        col.str.strip_prefix(res.value).alias(col_name)
                    )
                    dtypes.append(ColumnDataType.NUMBER)
                    currencies.append(res)
                elif possibly_gender_column(string_vals):
                    df = df.with_columns(
                        col.map_elements(
                            lambda val: normalize_gender_column(val),
                            return_dtype=pl.String,
                        )
                    )
                    dtypes.append(ColumnDataType.STRING)
                    currencies.append(None)
                else:
                    df = df.with_columns(
                        col.map_elements(
                            lambda val: fix_possible_misspellings(val, col),
                            return_dtype=pl.String,
                        )
                    )
                    dtypes.append(ColumnDataType.STRING)
                    currencies.append(None)
            case dtype.Boolean:
                dtypes.append(ColumnDataType.BOOLEAN)
                currencies.append(None)
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
                currencies.append(None)
            case _:
                dtypes.append(ColumnDataType.STRING)
                currencies.append(None)
        col = df.get_column(col_name)
        labels.append(col_name)
        rows.append(",".join(col.cast(dtype.String).to_list()))
    return df.write_csv(), labels, rows, dtypes, currencies


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
    return true_count + false_count > total_count * COUNT_THRESHOLD


def possibly_currency_column(string_vals: list[str]) -> CurrencySymbol | None:
    "returns currency symbol if found. None if none"
    threshold = len(string_vals) * COUNT_THRESHOLD
    ret: CurrencySymbol | None = None
    currency_symbol: CurrencySymbol | None = None
    found_count = 0
    for val in string_vals:
        if val in [""]:
            continue
        for symbol in iter(CurrencySymbol):
            if val.startswith(symbol):
                if currency_symbol is None:
                    currency_symbol = symbol
                elif currency_symbol != symbol:
                    # many different symbols in column. do not bother trying to convert
                    return None
                ret = symbol
                try:
                    float(val[len(symbol) :])
                except ValueError:
                    # not a valid currency number
                    return None
                found_count += 1
                break
    return ret if found_count > threshold else None


def possibly_gender_column(string_vals: list[str]) -> bool:
    male_count = sum(1 for x in string_vals if x in GENDER_MALE_VALUES)
    female_count = sum(1 for x in string_vals if x in GENDER_MALE_VALUES)
    total_count = len(string_vals)
    return male_count + female_count > total_count * COUNT_THRESHOLD


def normalize_gender_column(original: str) -> str:
    if original in GENDER_MALE_VALUES:
        return "male"
    elif original in GENDER_FEMALE_VALUES:
        return "female"
    return original


def fix_possible_misspellings(original: str, col: Series) -> str:
    if (mode := col.mode().first()) is None:
        return original
    mode = str(mode)
    if SequenceMatcher(None, original, mode).ratio() > SIMILARITY_THRESHOLD:
        return mode

    similar_vals: list[str] = []
    for other in col:
        if SequenceMatcher(None, original, other).ratio() > SIMILARITY_THRESHOLD:
            similar_vals.append(other)

    if res := Counter(similar_vals).most_common(1):
        return res[0][0]
    return original
