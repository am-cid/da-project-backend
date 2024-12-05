from typing import Annotated, Counter, List

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app.database import SessionDep
from app.models import Column, ColumnResponse
from app.types import ColumnDataType, ColumnOperation, CurrencySymbol

router = APIRouter(prefix="/api/report/{report_id}/column", tags=["column"])


@router.get("/")
def get_report_columns(
    report_id: int,
    session: SessionDep,
    labels: str | None = None,
    dtype: ColumnDataType | None = None,
    currency: CurrencySymbol | None = None,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> List[ColumnResponse]:
    statement = select(Column.label, Column.dtype, Column.currency, Column.rows).where(
        Column.report_id == report_id,
    )
    if labels:
        statement = statement.where(col(Column.label).in_(set(labels.split(","))))
    if dtype:
        statement = statement.where(Column.dtype == dtype)
    if currency:
        statement = statement.where(Column.currency == currency)
    res = session.exec(statement.offset(offset).limit(limit)).all()
    return [
        ColumnResponse(
            label=label,
            column_type=ColumnDataType(row_type),
            rows=rows.split(",") if rows else [],
            currency=CurrencySymbol.from_str(currency),
        )
        for label, row_type, currency, rows in res
    ]


@router.get(
    "/{label}",
    description=r"""
If no operation is specified, this will return `array<number> | array<string> | array<bool>`.
Response type is dependent on optional operation query param.

Certain operations require a specific column datatype. Mismatching types will
return a 422 Unprocessable Content
| operation | column datatype | response type |
|-|-|-|
| no operation specified | number, string, bool | array\<number\>, array\<string\>, array\<bool\> |
| first | number, string, bool | number, string, bool |
| last | number, string, bool | number, string, bool |
| max | number | number |
| mean | number | number |
| median | number | number |
| min | number | number |
| mode | number | array\<number\> |
| sum | number | number |
""",
)
def get_report_column_data_by_label(
    report_id: int,
    label: str,
    session: SessionDep,
    operation: ColumnOperation | None = None,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[bool] | list[float] | list[str] | bool | float | str:
    res = session.exec(
        select(Column.rows, Column.dtype)
        .where(
            Column.report_id == report_id,
            Column.label == label,
        )
        .offset(offset)
        .limit(limit),
    ).first()
    if not res:
        raise HTTPException(
            status_code=404,
            detail=f"No columns in report '{report_id}' found",
        )
    (row, dtype) = res
    if not row or "".join(set(list(row))) == ",":
        raise HTTPException(
            status_code=422,
            detail=f"Column does exist in report '{report_id}' but no rows are found (empty column)",
        )
    match dtype:
        case ColumnDataType.BOOLEAN:
            return _handle_bool_column(row, operation)
        case ColumnDataType.NUMBER:
            return _handle_number_column(row, operation)
        case ColumnDataType.STRING:
            return _handle_string_column(row, operation)
        case _:
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error. Unknown row data type '{dtype}'",
            )


def _handle_string_column(
    row: str,
    operation: ColumnOperation | None,
) -> list[str] | str | int:
    row_data = row.split(",")
    match operation:
        case None:
            return row_data
        case ColumnOperation.FIRST:
            return row_data[0]
        case ColumnOperation.LAST:
            return row_data[len(row_data) - 1]
        case _:
            raise HTTPException(
                status_code=422,
                detail=f"Row operation '{operation}' is impossible for row data type 'string'",
            )


def _handle_bool_column(
    row: str,
    operation: ColumnOperation | None,
) -> list[bool] | bool | int:
    row_data = list(map(bool, row.split(",")))
    match operation:
        case None:
            return row_data
        case ColumnOperation.FIRST:
            return row_data[0]
        case ColumnOperation.LAST:
            return row_data[len(row_data) - 1]
        case _:
            raise HTTPException(
                status_code=422,
                detail=f"Row operation '{operation}' is impossible for row data type 'bool'",
            )


def _handle_number_column(
    row: str,
    operation: ColumnOperation | None,
) -> list[float] | float | int:
    row_data = list(map(float, row.split(",")))
    if not operation:
        return row_data
    match operation:
        case ColumnOperation.FIRST:
            return row_data[0]
        case ColumnOperation.LAST:
            return row_data[len(row_data) - 1]
        case ColumnOperation.MAX:
            return max(row_data)
        case ColumnOperation.MEAN:
            return sum(row_data) / len(row_data)
        case ColumnOperation.MEDIAN:
            row_data.sort()
            n = len(row_data)
            if n % 2 != 0:
                return row_data[n // 2]
            mid_1 = row_data[(n // 2) - 1]
            mid_2 = row_data[(n // 2)]
            return (mid_1 + mid_2) / 2
        case ColumnOperation.MIN:
            return min(row_data)
        case ColumnOperation.MODE:
            counts = Counter(row_data)
            max_freq = max(counts.values())
            modes = [key for key, val in counts.items() if val == max_freq]
            return modes
        case ColumnOperation.SUM:
            return sum(row_data)
