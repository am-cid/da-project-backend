from typing import Annotated, List

from fastapi import APIRouter, File, HTTPException, Query
from sqlmodel import select

from app.database import SessionDep
from app.models import (
    ColumnCreate,
    ColumnResponse,
    Report,
    ReportCreate,
    ReportResponse,
    ReportUpdate,
    ReportWithColumnsResponse,
)

from .gemini import prompt_gemini

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/")
def get_all_reports(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> List[ReportResponse]:
    reports = session.exec(select(Report).offset(offset).limit(limit)).all()
    return ReportResponse.from_reports(reports)


@router.post("/")
def add_report(
    report: Annotated[ReportCreate, File()],
    session: SessionDep,
) -> ReportWithColumnsResponse:
    db_report, labels, rows, dtypes = report.validate_to_report()
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


@router.get("/{report_id}")
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


@router.patch("/{report_id}")
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


@router.delete("/{report_id}")
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
