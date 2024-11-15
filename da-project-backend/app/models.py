from __future__ import annotations

from typing import Literal

from sqlmodel import (
    DateTime,
    Field,
    LargeBinary,
    Relationship,
    SQLModel,
)


class Source(SQLModel, table=True):
    source_id: int | None = Field(default=None, primary_key=True)
    raw_csv: LargeBinary | None = Field(default=None)

    reports: list[Report] = Relationship(back_populates="source", cascade_delete=True)
    columns: list[Column] = Relationship(back_populates="source", cascade_delete=True)


class Report(SQLModel, table=True):
    report_id: int | None = Field(default=None, primary_key=True)
    text: str = Field(default="")

    source_id: int = Field(foreign_key="source.source_id", ondelete="CASCADE")
    source: Source = Relationship(back_populates="reports")
    remarks: list[Remark] = Relationship(back_populates="report", cascade_delete=True)


class Column(SQLModel, table=True):
    column_id: int | None = Field(default=None, primary_key=True)
    header: str = Field(default="")
    rows: LargeBinary | None = Field(default=None)
    dtype: Literal["NUMBER", "BOOLEAN", "STRING"] = Field(default="NUMBER")

    source_id: int = Field(foreign_key="source.source_id", ondelete="CASCADE")
    source: Source = Relationship(back_populates="columns")


class Remark(SQLModel, table=True):
    remark_id: int | None = Field(default=None, primary_key=True)
    remark: str = Field(default="")
    created_at: DateTime | None = Field(default=None)
    updated_at: DateTime | None = Field(default=None)

    report_id: int = Field(foreign_key="report.report_id", ondelete="CASCADE")
    report: Report = Relationship(back_populates="remarks")
