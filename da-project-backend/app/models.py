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


## REPORT MODELS
class ReportFields(SQLModel):
    report_id: int | None = Field(default=None, primary_key=True)
    report_overview: str = Field(default="")
    raw_csv: str = Field(default="")

    def to_report(self) -> "Report":
        valid = self.model_validate(self)
        return Report(
            report_overview=valid.report_overview,
            raw_csv=valid.raw_csv,
        )


class Report(ReportFields, table=True):
    pages: List["Page"] = Relationship(back_populates="report", cascade_delete=True)
    columns: List["Column"] = Relationship(back_populates="report", cascade_delete=True)


class ReportResponse(BaseModel):
    id: int
    overview: str

    @staticmethod
    def from_report(report: Report) -> "ReportResponse":
        return ReportResponse(
            id=report.report_id if report.report_id is not None else 0,
            overview=report.report_overview,
        )

    @staticmethod
    def from_reports(reports: Sequence[Report]) -> "List[ReportResponse]":
        return [ReportResponse.from_report(report) for report in reports]


class ReportCreate(BaseModel):
    overview: str
    csv: str

    def validate_to_report(self) -> Report:
        return ReportFields(
            report_overview=self.overview,
            raw_csv=self.csv,
        ).to_report()


## PAGE MODELS
class PageChartType(enum.StrEnum):
    BAR_CHART = "BAR_CHART"
    PIE_CHART = "PIE_CHART"
    TREND_CHART = "TREND_CHART"
    SCATTER_PLOT = "SCATTER_PLOT"


class PageFields(SQLModel):
    page_id: int | None = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="report.report_id", ondelete="CASCADE")
    page_name: str = Field(default="")
    page_overview: str = Field(default="")
    chart_type: PageChartType = Field(sa_column=Col(Enum(PageChartType)))
    labels: str = Field(default="")


class Page(PageFields, table=True):
    report: Report = Relationship(back_populates="pages")
    comments: List["Comment"] = Relationship(back_populates="page", cascade_delete=True)


class PageResponse(BaseModel):
    id: int
    name: str
    overview: str
    chart_type: str
    labels: list[str]

    @staticmethod
    def from_page(page: Page) -> "PageResponse":
        return PageResponse(
            id=page.page_id if page.page_id is not None else 0,
            name=page.page_name,
            overview=page.page_overview,
            chart_type=page.chart_type,
            labels=page.labels.split(","),
        )

    @staticmethod
    def from_pages(pages: Sequence[Page]) -> "List[PageResponse]":
        return [PageResponse.from_page(page) for page in pages]


## COLUMN MODELS
class ColumnDataType(enum.StrEnum):
    BOOLEAN = "BOOLEAN"
    NUMBER = "NUMBER"
    STRING = "STRING"


class ColumnFields(SQLModel):
    column_id: int | None = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="report.report_id", ondelete="CASCADE")
    label: str = Field(default="")
    rows: str | None = Field(default=None)
    dtype: ColumnDataType = Field(
        default=ColumnDataType.STRING, sa_column=Col(Enum(ColumnDataType))
    )


class Column(ColumnFields, table=True):
    report: Report = Relationship(back_populates="columns")


class ColumnResponse(BaseModel):
    label: str
    rows: list[str]
    row_type: str

    @staticmethod
    def from_column(column: Column) -> "ColumnResponse":
        return ColumnResponse(
            label=column.label,
            rows=column.rows.split(",") if column.rows else [],
            row_type=column.dtype,
        )

    @staticmethod
    def from_columns(columns: Sequence[Column]) -> "List[ColumnResponse]":
        return [ColumnResponse.from_column(column) for column in columns]


## COMMENT MODELS
class CommentFields(SQLModel):
    comment: str = Field(default="")
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
    page_id: int = Field(foreign_key="page.page_id", ondelete="CASCADE")

    def to_comment(self) -> "Comment":
        valid = self.model_validate(self)
        return Comment(
            comment=valid.comment,
            created_at=valid.created_at,
            updated_at=valid.updated_at,
            page_id=valid.page_id,
        )


class Comment(CommentFields, table=True):
    comment_id: int | None = Field(default=None, primary_key=True)
    page: Page = Relationship(back_populates="comments")


class CommentResponse(BaseModel):
    id: int
    comment: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_comment(comment: Comment) -> "CommentResponse":
        return CommentResponse(
            id=comment.comment_id if comment.comment_id is not None else 0,
            comment=comment.comment,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )

    @staticmethod
    def from_comments(remarks: Sequence[Comment]) -> "List[CommentResponse]":
        return [CommentResponse.from_comment(column) for column in remarks]

    @staticmethod
    def from_report(page: Page) -> "List[CommentResponse]":
        return CommentResponse.from_comments(page.comments)


class CommentCreate(BaseModel):
    remark: str

    def validate_to_comment(self, page_id: int) -> Comment:
        return CommentFields(
            comment=self.remark,
            page_id=page_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ).to_comment()
