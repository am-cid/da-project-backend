from typing import Annotated, List

from fastapi import FastAPI, HTTPException, Query
from sqlmodel import select

from .database import SessionDep
from .models import (
    Remark,
    RemarkCreate,
    RemarkResponse,
    Report,
    ReportResponse,
)

app = FastAPI()


@app.get("/api/report")
def get_all_reports(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> List[ReportResponse]:
    reports = session.exec(select(Report).offset(offset).limit(limit)).all()
    return ReportResponse.from_reports(reports)


@app.get("/api/report/{report_id}")
def get_report(
    report_id: int,
    session: SessionDep,
) -> ReportResponse:
    report = session.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportResponse.from_report(report)


@app.get("/api/report/{report_id}/comments")
def get_report_remarks(
    report_id: int,
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> List[RemarkResponse]:
    remarks = session.exec(
        select(Remark).where(Remark.report_id == report_id).offset(offset).limit(limit)
    ).all()
    return RemarkResponse.from_remarks(remarks)


@app.post("/api/report/{report_id}/comments")
def post_report_remark(
    report_id: int,
    remark: RemarkCreate,
    session: SessionDep,
) -> RemarkResponse:
    db_remark = remark.validate_to_remark(report_id)
    session.add(db_remark)
    session.commit()
    session.refresh(db_remark)
    return RemarkResponse.from_remark(db_remark)
