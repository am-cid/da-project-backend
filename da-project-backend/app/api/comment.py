from typing import Annotated, List

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from app.database import SessionDep
from app.models import (
    Comment,
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    Page,
    Report,
)

router = APIRouter(
    prefix="/api/report/{report_id}/page/{page_id}/comment", tags=["comment"]
)


@router.get("/")
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


@router.post("/")
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


@router.patch("/{comment_id}")
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
            detail=f"Comment from report '{report_id}' page '{page_id}' with"
            f"id '{comment_id}' not found",
        )
    update.apply_to(original)
    session.add(original)
    session.commit()
    session.refresh(original)
    return CommentResponse.from_comment(original)


@router.delete("/{comment_id}")
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
            detail=f"Comment from report '{report_id}' page '{page_id}' with"
            f"id '{comment_id}' not found",
        )
    session.delete(original)
    session.commit()
    return CommentResponse.from_comment(original)
