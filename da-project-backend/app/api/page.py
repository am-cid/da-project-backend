from typing import Annotated, List

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from app.database import SessionDep
from app.models import (
    Page,
    PageCreate,
    PageResponse,
    PageUpdate,
)

from .column import get_report_columns
from .gemini import prompt_gemini

router = APIRouter(prefix="/api/report/{report_id}/page", tags=["page"])


@router.get("/")
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


@router.post("/")
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


@router.get("/{page_id}")
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


@router.patch("/{page_id}")
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


@router.delete("/{page_id}")
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
