from typing import Any

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    source_text: str | None = None
    page_number: int | None = None


class ExtractedLineItem(BaseModel):
    line_item: str
    schedule: str | None = None
    values: dict[str, Any] = Field(
        default_factory=dict
    )
    evidence: Evidence | None = None
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


class ExtractedSection(BaseModel):
    section_name: str
    line_items: list[ExtractedLineItem] = Field(
        default_factory=list
    )


class FinancialStatement(BaseModel):
    sections: list[ExtractedSection] = Field(
        default_factory=list
    )


class ExtractedDocument(BaseModel):
    document_type: str
    as_at_date: str | None = None
    unit_of_measurement: str | None = None
    comparative_periods: list[str] = Field(
        default_factory=list
    )
    financial_statement: FinancialStatement = Field(
        default_factory=FinancialStatement
    )
    notes: list[str | dict[str, Any]] = Field(
        default_factory=list
    )
    signatures_and_attestation: dict[str, Any] = Field(
        default_factory=dict
    )
    document_footer: dict[str, Any] = Field(
        default_factory=dict
    )