"""
Pydantic schemas for API contracts.

We keep these centralized in a single file for hackathon velocity and easy review
by judges. If this evolves, split into a package.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class DatasetProfile(BaseModel):
    dataset_id: str
    table_name: str
    source: Literal["demo", "upload"]
    original_filename: Optional[str] = None

    row_count: int
    column_count: int
    columns: List[str]
    numeric_columns: List[str]
    categorical_columns: List[str]
    date_columns: List[str]
    preview_rows: List[Dict[str, Any]]


class GenerateDashboardRequest(BaseModel):
    dataset_id: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=3, max_length=600)


class FollowUpRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=600)


class SummaryCard(BaseModel):
    label: str
    value: Any


class SqlQuerySpec(BaseModel):
    id: str
    title: str
    intent: str
    sql: str


class ChartSpec(BaseModel):
    id: str
    title: str
    chartType: Literal[
        "line",
        "bar",
        "stacked_bar",
        "area",
        "pie",
        "table",
    ]
    xKey: Optional[str] = None
    yKeys: List[str] = Field(default_factory=list)
    data: List[Dict[str, Any]] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)


class DashboardSpec(BaseModel):
    title: str
    summary_cards: List[SummaryCard] = Field(default_factory=list)
    charts: List[ChartSpec] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)
    sql_queries: List[SqlQuerySpec] = Field(default_factory=list)
    message: Optional[str] = None


class GenerateDashboardResponse(BaseModel):
    dashboard: DashboardSpec
    session_id: str
    warnings: List[str] = Field(default_factory=list)


class FollowUpResponse(BaseModel):
    dashboard: DashboardSpec
    warnings: List[str] = Field(default_factory=list)


class DatasetSchemaColumn(BaseModel):
    name: str
    sqlite_type: str


class DatasetSchemaResponse(BaseModel):
    dataset_id: str
    table_name: str
    columns: List[DatasetSchemaColumn]


class DatasetPreviewResponse(BaseModel):
    dataset_id: str
    table_name: str
    rows: List[Dict[str, Any]]


class DatasetsListResponse(BaseModel):
    datasets: List[DatasetProfile]

