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
