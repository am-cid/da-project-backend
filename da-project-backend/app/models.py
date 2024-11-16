import enum
from datetime import datetime
from typing import List, Sequence

from pydantic import BaseModel
from sqlmodel import (
    TIMESTAMP,
    Enum,
    Field,
    Relationship,
    SQLModel,
    text,
)
from sqlmodel import Column as Col

"""
MODEL STRUCTURE
TableFields:
    contains table fields

Table:
    most of the time, contains just relationships
    name it how you would name a table in the db

TableResponse:
    response structure

TableCreate: # optional (not all allows entry creation through api)
    request body structure of entry creation in table

...and other operations you might need (e.g., TableDelete, TableUpdate, etc.)

NOTE:
1. it is structured like this because Table (which will be the one created in db)
   cannot validate fields (why sqlmodel????) so we delegate that to TableFields
"""


## SOURCE MODELS
class SourceFields(SQLModel):
    source_id: int | None = Field(default=None, primary_key=True)
    raw_csv: str = Field(default="")


class Source(SourceFields, table=True):
    reports: List["Report"] = Relationship(back_populates="source", cascade_delete=True)
    columns: List["Column"] = Relationship(back_populates="source", cascade_delete=True)


## REPORT MODELS
class ReportFields(SQLModel):
    report_id: int | None = Field(default=None, primary_key=True)
    text: str = Field(default="")
    source_id: int = Field(foreign_key="source.source_id", ondelete="CASCADE")


class Report(ReportFields, table=True):
    source: Source = Relationship(back_populates="reports")
    remarks: List["Remark"] = Relationship(back_populates="report", cascade_delete=True)


class ReportResponse(BaseModel):
    id: int
    report: str

    @staticmethod
    def from_report(report: Report) -> "ReportResponse":
        return ReportResponse(
            id=report.report_id if report.report_id is not None else 0,
            report=report.text,
        )

    @staticmethod
    def from_reports(reports: Sequence[Report]) -> "List[ReportResponse]":
        return [ReportResponse.from_report(report) for report in reports]


## COLUMN MODELS
class ColumnDataType(enum.StrEnum):
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    STRING = "STRING"


class ColumnFields(SQLModel):
    column_id: int | None = Field(default=None, primary_key=True)
    header: str = Field(default="")
    rows: str | None = Field(default=None)
    dtype: ColumnDataType = Field(sa_column=Col(Enum(ColumnDataType)))
    source_id: int = Field(foreign_key="source.source_id", ondelete="CASCADE")


class Column(ColumnFields, table=True):
    source: Source = Relationship(back_populates="columns")


class ColumnResponse(BaseModel):
    id: int
    header: str
    rows: list[str]
    row_type: str

    @staticmethod
    def from_column(column: Column) -> "ColumnResponse":
        return ColumnResponse(
            id=column.column_id if column.column_id is not None else 0,
            header=column.header,
            rows=column.rows.split(",") if column.rows else [],
            row_type=column.dtype,
        )

    @staticmethod
    def from_columns(columns: Sequence[Column]) -> "List[ColumnResponse]":
        return [ColumnResponse.from_column(column) for column in columns]


## REMARK MODELS
class RemarkFields(SQLModel):
    remark: str = Field(default="")
    created_at: datetime = Field(
        sa_column=Col(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    updated_at: datetime = Field(
        sa_column=Col(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=text("CURRENT_TIMESTAMP"),
        )
    )
    report_id: int = Field(foreign_key="report.report_id", ondelete="CASCADE")

    def to_remark(self) -> "Remark":
        valid = self.model_validate(self)
        return Remark(
            remark=valid.remark,
            created_at=valid.created_at,
            updated_at=valid.updated_at,
            report_id=valid.report_id,
        )


class Remark(RemarkFields, table=True):
    remark_id: int | None = Field(default=None, primary_key=True)
    report: Report = Relationship(back_populates="remarks")


class RemarkResponse(BaseModel):
    id: int
    remark: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_remark(remark: Remark) -> "RemarkResponse":
        return RemarkResponse(
            id=remark.remark_id if remark.remark_id is not None else 0,
            remark=remark.remark,
            created_at=remark.created_at,
            updated_at=remark.updated_at,
        )

    @staticmethod
    def from_remarks(remarks: Sequence[Remark]) -> "List[RemarkResponse]":
        return [RemarkResponse.from_remark(column) for column in remarks]

    @staticmethod
    def from_report(report: Report) -> "List[RemarkResponse]":
        return RemarkResponse.from_remarks(report.remarks)


class RemarkCreate(BaseModel):
    remark: str

    def validate_to_remark(self, report_id: int) -> Remark:
        return RemarkFields(
            remark=self.remark,
            report_id=report_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ).to_remark()
