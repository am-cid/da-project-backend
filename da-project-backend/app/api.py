from typing import Annotated, List

from fastapi import FastAPI, HTTPException, Query
from sqlmodel import select

from .database import SessionDep
from .models import (
    Comment,
    CommentCreate,
    CommentResponse,
    Page,
    PageResponse,
)

app = FastAPI()


@app.get("/api/report")
def get_all_reports(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> List[PageResponse]:
    reports = session.exec(select(Page).offset(offset).limit(limit)).all()
    return PageResponse.from_pages(reports)


@app.get("/api/report/{report_id}")
def get_report(
    report_id: int,
    session: SessionDep,
) -> PageResponse:
    report = session.get(Page, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return PageResponse.from_page(report)


@app.get("/api/report/{report_id}/comments")
def get_report_remarks(
    report_id: int,
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> List[CommentResponse]:
    remarks = session.exec(
        select(Comment).where(Comment.page_id == report_id).offset(offset).limit(limit)
    ).all()
    return CommentResponse.from_comments(remarks)


@app.post("/api/report/{report_id}/comments")
def post_report_remark(
    report_id: int,
    remark: CommentCreate,
    session: SessionDep,
) -> CommentResponse:
    db_remark = remark.validate_to_comment(report_id)
    session.add(db_remark)
    session.commit()
    session.refresh(db_remark)
    return CommentResponse.from_comment(db_remark)
