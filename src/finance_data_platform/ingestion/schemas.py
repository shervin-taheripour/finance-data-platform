"""Pydantic data contracts for ingestion boundary records."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Ticker = Annotated[str, Field(min_length=1, max_length=16, pattern=r"^[A-Za-z0-9.\-]+$")]
NonNegativeFloat = Annotated[float, Field(ge=0)]
PositiveFloat = Annotated[float, Field(gt=0)]
NonNegativeInt = Annotated[int, Field(ge=0)]


class BaseSchema(BaseModel):
    """Base schema with strict field handling."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OHLCVRecord(BaseSchema):
    """Single OHLCV row for a symbol and trading date."""

    symbol: Ticker
    date: date
    open: NonNegativeFloat
    high: NonNegativeFloat
    low: NonNegativeFloat
    close: NonNegativeFloat
    adj_close: NonNegativeFloat | None = None
    volume: NonNegativeInt
    source: str = "yfinance"

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.upper()

    @field_validator("date")
    @classmethod
    def not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("date cannot be in the future")
        return value

    @model_validator(mode="after")
    def validate_price_ranges(self) -> OHLCVRecord:
        if self.high < self.low:
            raise ValueError("high must be greater than or equal to low")
        if not (self.low <= self.open <= self.high):
            raise ValueError("open must be between low and high")
        if not (self.low <= self.close <= self.high):
            raise ValueError("close must be between low and high")
        return self


class DividendRecord(BaseSchema):
    """Single dividend event."""

    symbol: Ticker
    ex_date: date
    amount: PositiveFloat
    currency: str | None = None
    source: str = "yfinance"

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.upper()

    @field_validator("ex_date")
    @classmethod
    def not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("ex_date cannot be in the future")
        return value


class SplitRecord(BaseSchema):
    """Single split event represented as ratio."""

    symbol: Ticker
    ex_date: date
    split_ratio: PositiveFloat
    source: str = "yfinance"

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.upper()

    @field_validator("ex_date")
    @classmethod
    def not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("ex_date cannot be in the future")
        return value


class SecurityMetadata(BaseSchema):
    """Reference metadata for a symbol."""

    symbol: Ticker
    short_name: str | None = None
    long_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    currency: str | None = None
    exchange: str | None = None
    market_cap: NonNegativeInt | None = None
    shares_outstanding: NonNegativeInt | None = None
    as_of_date: date | None = None
    source: str = "yfinance"

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.upper()

    @field_validator("as_of_date")
    @classmethod
    def as_of_not_in_future(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("as_of_date cannot be in the future")
        return value
