from collections import Counter
from contextlib import asynccontextmanager
from typing import Annotated, List, Literal

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query
from sqlmodel import col, select

from .database import SessionDep, create_db_and_tables
from .models import (
    Column,
    ColumnCreate,
    ColumnResponse,
    Comment,
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    Page,
    PageCreate,
    PageResponse,
    PageUpdate,
    Report,
    ReportCreate,
    ReportResponse,
    ReportUpdate,
    ReportWithColumnsResponse,
)
from .types import ColumnDataType, ColumnOperation


@asynccontextmanager
async def lifespan(_: FastAPI):
    # startup
    create_db_and_tables()
    load_dotenv()
    genai.configure()
    # end startup
    yield
    # shutdown
    # end shutdown


app = FastAPI(lifespan=lifespan)


@app.get("/api/report")
def get_all_reports(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> List[ReportResponse]:
    reports = session.exec(select(Report).offset(offset).limit(limit)).all()
    return ReportResponse.from_reports(reports)


@app.post("/api/report")
def add_report(
    report: Annotated[ReportCreate, File()],
    session: SessionDep,
) -> ReportWithColumnsResponse:
    db_report, labels, rows, dtypes = ReportCreate(
        name=report.name,
        csv_upload=report.csv_upload,
    ).validate_to_report()
    db_report.report_overview = prompt_gemini(
        session,
        prompt="Given this data and a hypothetical report made using it, give"
        "an overview of the report as if it is already done.",
        context={"data": db_report.clean_csv},
    )
    session.add(db_report)
    session.commit()
    session.refresh(db_report)
    assert db_report.report_id is not None
    columns = ColumnCreate.create_columns(db_report.report_id, labels, rows, dtypes)
    for column in columns:
        session.add(column)
        session.commit()
        session.refresh(column)
    return ReportWithColumnsResponse(
        report=ReportResponse.from_report(db_report),
        columns=ColumnResponse.from_columns(columns),
    )


@app.get("/api/report/{report_id}")
def get_report(
    report_id: int,
    session: SessionDep,
) -> ReportResponse:
    report = session.exec(
        select(Report).where(Report.report_id == report_id).offset(0).limit(1),
    ).first()
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Report with id '{report_id}' not found",
        )
    return ReportResponse.from_report(report)


@app.patch("/api/report/{report_id}")
def update_report(
    report_id: int,
    update: ReportUpdate,
    session: SessionDep,
) -> ReportResponse:
    original = session.exec(
        select(Report).where(Report.report_id == report_id).offset(0).limit(1),
    ).first()
    if not original:
        raise HTTPException(
            status_code=404,
            detail=f"Report with id '{report_id}' not found",
        )
    update.apply_to(original)
    session.add(original)
    session.commit()
    session.refresh(original)
    return ReportResponse.from_report(original)


@app.delete("/api/report/{report_id}")
def delete_report(
    report_id: int,
    session: SessionDep,
) -> ReportResponse:
    original = session.exec(
        select(Report).where(Report.report_id == report_id).offset(0).limit(1),
    ).first()
    if not original:
        raise HTTPException(
            status_code=404,
            detail=f"Report with id '{report_id}' not found",
        )
    session.delete(original)
    session.commit()
    return ReportResponse.from_report(original)


@app.get("/api/report/{report_id}/page")
def get_all_report_pages(
    report_id: int,
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> List[PageResponse]:
    pages = session.exec(
        select(Page).where(Page.report_id == report_id).offset(offset).limit(limit),
    ).all()
    return PageResponse.from_pages(pages)


@app.post("/api/report/{report_id}/page")
def add_report_page(
    report_id: int,
    page: PageCreate,
    session: SessionDep,
) -> PageResponse:
    columns = get_report_columns(report_id, session, page.labels)
    columns_ctx = "\n".join(
        list(
            map(
                lambda x: x.model_dump_json(),
                columns,
            )
        )
    )
    overview = prompt_gemini(
        session,
        prompt="Given this data and a hypothetical report page made using it, "
        "give an overview of the report page as if it is already done.",
        context={
            "page_name": page.name,
            "columns": columns_ctx,
            "chart_type": page.chart_type,
        },
    )
    db_page = page.validate_to_page(report_id, overview)
    session.add(db_page)
    session.commit()
    session.refresh(db_page)
    return PageResponse.from_page(db_page)


@app.get("/api/report/{report_id}/page/{page_id}")
def get_report_page(
    report_id: int,
    page_id: int,
    session: SessionDep,
) -> PageResponse:
    page = session.exec(
        select(Page)
        .where(Page.report_id == report_id)
        .where(Page.page_id == page_id)
        .offset(0)
        .limit(1),
    ).first()
    if not page:
        raise HTTPException(
            status_code=404,
            detail=f"Page from report '{report_id}' with id '{page_id}' not found",
        )
    return PageResponse.from_page(page)


@app.patch("/api/report/{report_id}/page/{page_id}")
def update_report_page(
    report_id: int,
    page_id: int,
    update: PageUpdate,
    session: SessionDep,
) -> PageResponse:
    original = session.exec(
        select(Page)
        .where(Page.report_id == report_id, Page.page_id == page_id)
        .offset(0)
        .limit(1),
    ).first()
    if not original:
        raise HTTPException(
            status_code=404,
            detail=f"Page from report '{report_id}' with id '{page_id}' not found",
        )
    update.apply_to(original)
    session.add(original)
    session.commit()
    session.refresh(original)
    return PageResponse.from_page(original)


@app.delete("/api/report/{report_id}/page/{page_id}")
def delete_report_page(
    report_id: int,
    page_id: int,
    session: SessionDep,
) -> PageResponse:
    original = session.exec(
        select(Page)
        .where(Page.report_id == report_id, Page.page_id == page_id)
        .offset(0)
        .limit(1),
    ).first()
    if not original:
        raise HTTPException(
            status_code=404,
            detail=f"Page from report '{report_id}' with id '{page_id}' not found",
        )
    session.delete(original)
    session.commit()
    return PageResponse.from_page(original)


@app.get("/api/report/{report_id}/page/{page_id}/comment")
def get_all_report_page_comments(
    report_id: int,
    page_id: int,
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> List[CommentResponse]:
    comments = session.exec(
        select(Comment)
        .join(Page)
        .where(Page.report_id == report_id, Comment.page_id == page_id)
        .offset(offset)
        .limit(limit),
    ).all()
    return CommentResponse.from_comments(comments)


@app.post("/api/report/{report_id}/page/{page_id}/comment")
def add_report_page_comment(
    report_id: int,
    page_id: int,
    comment: CommentCreate,
    session: SessionDep,
) -> CommentResponse:
    exists = session.exec(
        select(Report).where(Report.report_id == report_id).offset(0).limit(1),
    ).first()
    if not exists:
        raise HTTPException(
            status_code=404,
            detail=f"Page from report '{report_id}' with id '{page_id}' not found",
        )
    db_comment = comment.validate_to_comment(page_id)
    session.add(db_comment)
    session.commit()
    session.refresh(db_comment)
    return CommentResponse.from_comment(db_comment)


@app.patch("/api/report/{report_id}/page/{page_id}/comment/{comment_id}")
def update_report_page_comment(
    report_id: int,
    page_id: int,
    comment_id: int,
    update: CommentUpdate,
    session: SessionDep,
) -> CommentResponse:
    original = session.exec(
        select(Comment)
        .join(Page)
        .where(
            Page.report_id == report_id,
            Comment.page_id == page_id,
            Comment.comment_id == comment_id,
        )
        .offset(0)
        .limit(1),
    ).first()
    if not original:
        raise HTTPException(
            status_code=404,
            detail=f"Comment from report '{report_id}' page '{page_id}' with id '{comment_id}' not found",
        )
    update.apply_to(original)
    session.add(original)
    session.commit()
    session.refresh(original)
    return CommentResponse.from_comment(original)


@app.delete("/api/report/{report_id}/page/{page_id}/comment/{comment_id}")
def delete_report_page_comment(
    report_id: int,
    page_id: int,
    comment_id: int,
    session: SessionDep,
) -> CommentResponse:
    original = session.exec(
        select(Comment)
        .join(Page)
        .where(
            Page.report_id == report_id,
            Comment.page_id == page_id,
            Comment.comment_id == comment_id,
        )
        .offset(0)
        .limit(1),
    ).first()
    if not original:
        raise HTTPException(
            status_code=404,
            detail=f"Comment from report '{report_id}' page '{page_id}' with id '{comment_id}' not found",
        )
    session.delete(original)
    session.commit()
    return CommentResponse.from_comment(original)


@app.get("/api/report/{report_id}/column")
def get_report_columns(
    report_id: int,
    session: SessionDep,
    labels: str | None = None,
    dtype: ColumnDataType | None = None,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> List[ColumnResponse]:
    statement = select(Column.label, Column.dtype, Column.rows).where(
        Column.report_id == report_id,
    )
    if labels:
        statement = statement.where(col(Column.label).in_(set(labels.split(","))))
    if dtype:
        statement = statement.where(Column.dtype == dtype)
    res = session.exec(statement.offset(offset).limit(limit)).all()
    return [
        ColumnResponse(
            label=label,
            column_type=ColumnDataType(row_type),
            rows=rows.split(",") if rows else [],
        )
        for label, row_type, rows in res
    ]


@app.get(
    "/api/report/{report_id}/column/{label}",
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


@app.post("/api/gemini")
def prompt_gemini(
    _: SessionDep,
    *,
    prompt: str,
    context: dict[str, str] = {},
    model: Literal[
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
    ] = "gemini-1.5-flash",
) -> str:
    prompt = f"""
<system>
Since this request comes from an API, I expect to only get the answer without
acknowledgement from you. Do not use unsure tone and terms such as "likely",
"probably", etc. Keep it professional. Do not hallucinate.
</system>
<prompt>
{prompt}
</prompt>"""
    for tag, content in context.items():
        prompt += f"""
<{tag}>
{content}
</{tag}>
"""
    res = genai.GenerativeModel(model).generate_content(prompt)
    return res.text
