from datetime import datetime
from typing import List, Sequence

from fastapi import UploadFile
from process.clean import clean_csv
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

from .types import ColumnDataType, PageChartType

"""
MODEL STRUCTURE
TableFields:
    contains table fields

Table:
    most of the time, contains just relationships
    name it how you would name a table in the db

TableResponse:
    response structure

TableCreate:
    request body structure of entry creation in table

...and other operations you might need (e.g., TableDelete, TableUpdate, etc.)

NOTE:
1. it is structured like this because Table (which will be the one created in db)
   cannot model_validate fields (why sqlmodel?) so we delegate that to TableFields
"""


## REPORT MODELS
class ReportFields(SQLModel):
    report_id: int | None = Field(default=None, primary_key=True)
    report_name: str = Field(default="")
    report_overview: str = Field(default="")
    clean_csv: str = Field(default="")

    def to_report(self) -> "Report":
        valid = self.model_validate(self)
        return Report(
            report_name=valid.report_name,
            report_overview=valid.report_overview,
            clean_csv=valid.clean_csv,
        )


class Report(ReportFields, table=True):
    pages: List["Page"] = Relationship(back_populates="report", cascade_delete=True)
    columns: List["Column"] = Relationship(back_populates="report", cascade_delete=True)


class ReportResponse(BaseModel):
    id: int
    name: str
    overview: str

    @staticmethod
    def from_report(report: Report) -> "ReportResponse":
        return ReportResponse(
            id=report.report_id if report.report_id is not None else 0,
            name=report.report_name,
            overview=report.report_overview,
        )

    @staticmethod
    def from_reports(reports: Sequence[Report]) -> "List[ReportResponse]":
        return [ReportResponse.from_report(report) for report in reports]


class ReportCreate(BaseModel):
    name: str
    csv_upload: UploadFile
    model_config = {"extra": "forbid"}

    def validate_to_report(
        self,
    ) -> tuple[Report, list[str], list[str], list[ColumnDataType]]:
        """Returns:
        - validated Report
        - csv column labels
        - csv column rows (as comma separated string)
        - csv column dtype
        """
        cleaned_csv, labels, rows, dtypes = clean_csv(
            self.csv_upload.file.read().decode(),
        )
        return (
            ReportFields(
                report_name=self.name,
                clean_csv=cleaned_csv,
            ).to_report(),
            labels,
            rows,
            dtypes,
        )


class ReportWithColumnsResponse(BaseModel):
    report: ReportResponse
    columns: list["ColumnResponse"]


class ReportUpdate(BaseModel):
    name: str | None = None
    overview: str | None = None
    csv: str | None = None

    def apply_to(self, original: Report):
        if self.name is not None:
            original.report_name = self.name
        if self.overview is not None:
            original.report_overview = self.overview
        if self.csv is not None:
            original.clean_csv = self.csv
        original.model_validate(original)


## PAGE MODELS
class PageFields(SQLModel):
    page_id: int | None = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="report.report_id", ondelete="CASCADE")
    page_name: str = Field(default="")
    page_overview: str = Field(default="")
    chart_type: PageChartType = Field(sa_column=Col(Enum(PageChartType)))
    labels: str = Field(default="")

    def to_page(self) -> "Page":
        valid = self.model_validate(self)
        return Page(
            page_id=valid.page_id,
            report_id=valid.report_id,
            page_name=valid.page_name,
            page_overview=valid.page_overview,
            chart_type=valid.chart_type,
            labels=valid.labels,
        )


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


class PageCreate(BaseModel):
    name: str
    chart_type: PageChartType
    labels: str

    def validate_to_page(self, report_id: int, overview: str) -> Page:
        return PageFields(
            report_id=report_id,
            page_name=self.name,
            page_overview=overview,
            chart_type=self.chart_type,
            labels=self.labels,
        ).to_page()


class PageUpdate(BaseModel):
    name: str | None = None
    overview: str | None = None
    chart_type: PageChartType | None = None
    labels: str | None = None

    def apply_to(self, original: Page):
        if self.name is not None:
            original.page_name = self.name
        if self.overview is not None:
            original.page_overview = self.overview
        if self.chart_type is not None:
            original.chart_type = self.chart_type
        if self.labels is not None:
            original.labels = self.labels
        original.model_validate(original)


## COLUMN MODELS
class ColumnFields(SQLModel):
    column_id: int | None = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="report.report_id", ondelete="CASCADE")
    label: str = Field(default="")
    rows: str | None = Field(default=None)
    dtype: ColumnDataType = Field(
        default=ColumnDataType.STRING,
        sa_column=Col(Enum(ColumnDataType)),
    )

    def to_column(self) -> "Column":
        valid = self.model_validate(self)
        return Column(
            column_id=valid.column_id,
            report_id=valid.report_id,
            label=valid.label,
            rows=valid.rows,
            dtype=valid.dtype,
        )


class Column(ColumnFields, table=True):
    report: Report = Relationship(back_populates="columns")


class ColumnResponse(BaseModel):
    label: str
    rows: list[str]
    column_type: ColumnDataType

    @staticmethod
    def from_column(column: Column) -> "ColumnResponse":
        return ColumnResponse(
            label=column.label,
            rows=column.rows.split(",") if column.rows else [],
            column_type=column.dtype,
        )

    @staticmethod
    def from_columns(columns: Sequence[Column]) -> "List[ColumnResponse]":
        return [ColumnResponse.from_column(column) for column in columns]


class ColumnCreate(BaseModel):
    label: str
    rows: list[str]
    column_type: ColumnDataType

    def validate_to_column(self, report_id: int) -> Column:
        return ColumnFields(
            report_id=report_id,
            label=self.label,
            rows=",".join(self.rows),
            dtype=self.column_type,
        ).to_column()

    @staticmethod
    def create_columns(
        report_id: int,
        labels: list[str],
        rows: list[str],
        dtypes: list[ColumnDataType],
    ) -> list["Column"]:
        columns: list[Column] = []
        for label, rows_data, dtype in zip(labels, rows, dtypes):
            columns.append(
                ColumnCreate(
                    label=label,
                    rows=rows_data.split(","),
                    column_type=dtype,
                ).validate_to_column(report_id),
            )
        return columns


## COMMENT MODELS
class CommentFields(SQLModel):
    comment_id: int | None = Field(default=None, primary_key=True)
    comment: str = Field(default="")
    created_at: datetime = Field(
        sa_column=Col(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    updated_at: datetime = Field(
        sa_column=Col(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=text("CURRENT_TIMESTAMP"),
        ),
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
    comment: str

    def validate_to_comment(self, page_id: int) -> Comment:
        return CommentFields(
            comment=self.comment,
            page_id=page_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ).to_comment()


class CommentUpdate(BaseModel):
    comment: str | None = None

    def apply_to(self, original: Comment):
        if self.comment is not None:
            original.comment = self.comment
            original.updated_at = datetime.now()
        original.model_validate(original)
