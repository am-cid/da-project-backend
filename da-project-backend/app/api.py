import enum
from collections import Counter
from typing import Annotated, List

from fastapi import FastAPI, HTTPException, Query
from sqlmodel import col, select

from .database import SessionDep
from .models import (
    Column,
    ColumnDataType,
    ColumnResponse,
    Comment,
    CommentCreate,
    CommentResponse,
    Page,
    PageResponse,
)

app = FastAPI()


@app.get("/api/report-page")
def get_all_report_pages(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> List[PageResponse]:
    pages = session.exec(select(Page).offset(offset).limit(limit)).all()
    return PageResponse.from_pages(pages)


@app.get("/api/report-page/{page_id}")
def get_report_page(
    page_id: int,
    session: SessionDep,
) -> PageResponse:
    page = session.get(Page, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Report page not found")
    return PageResponse.from_page(page)


@app.get("/api/report-page/{page_id}/comments")
def get_page_comments(
    page_id: int,
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> List[CommentResponse]:
    comments = session.exec(
        select(Comment).where(Comment.page_id == page_id).offset(offset).limit(limit)
    ).all()
    return CommentResponse.from_comments(comments)


@app.post("/api/report-page/{page_id}/comments")
def post_page_comment(
    page_id: int,
    comment: CommentCreate,
    session: SessionDep,
) -> CommentResponse:
    db_comment = comment.validate_to_comment(page_id)
    session.add(db_comment)
    session.commit()
    session.refresh(db_comment)
    return CommentResponse.from_comment(db_comment)


@app.get("/api/report-page/{page_id}/column")
def get_report_page_columns(
    page_id: int,
    session: SessionDep,
    labels: str | None = None,
    dtype: ColumnDataType | None = None,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> List[ColumnResponse]:
    statement = (
        select(Column.label, Column.dtype, Column.rows)
        .select_from(Page, Column)
        .where(Page.page_id == page_id)
        .where(Column.report_id == Page.report_id)
    )
    if labels:
        statement = statement.where(col(Column.label).in_(set(labels.split(","))))
    if dtype:
        statement = statement.where(Column.dtype == dtype)
    res = session.exec(statement.offset(offset).limit(limit)).all()
    return [
        ColumnResponse(
            label=label,
            row_type=row_type,
            rows=rows.split(",") if rows else [],
        )
        for label, row_type, rows in res
    ]


class ColumnOperation(enum.StrEnum):
    SUM = "sum"
    MEAN = "mean"
    MEDIAN = "median"
    MODE = "mode"
    MAX = "max"
    MIN = "min"


@app.get(
    "/api/report-page/{page_id}/column/{label}",
    description="""
If no operation is specified, this will return `array<string> | null`.
Response type is dependent on optional operation query param.

If operation is set, the row data type in the db must be `"num"` or else this
will return `null`.

    operation = response type
    max = number
    mean = number
    median = number
    min = number
    mode = array<number>
    sum = number
""",
)
def get_report_page_column_data_by_label(
    page_id: int,
    label: str,
    session: SessionDep,
    operation: ColumnOperation | None = None,
) -> list[str] | list[float] | float | None:
    statement = (
        select(Column.rows, Column.dtype)
        .select_from(Page, Column)
        .where(Page.page_id == page_id)
        .where(Column.report_id == Page.report_id)
        .where(Column.label == label)
    )
    res = session.exec(statement).first()
    if not res:
        return None
    (row, dtype) = res
    if not row:
        return None
    row_data = row.split(",")
    if not operation:
        return row_data
    if dtype != ColumnDataType.NUMBER:
        return None
    row_data = list(map(float, row_data))
    match operation:
        case ColumnOperation.MAX:
            return max(row_data)
        case ColumnOperation.MEAN:
            return sum(row_data) / len(row_data)
        case ColumnOperation.MEDIAN:
            row_data.sort()
            n = len(row_data)
            if n % 2 != 0:
                return row_data[n // 2]
            else:
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
