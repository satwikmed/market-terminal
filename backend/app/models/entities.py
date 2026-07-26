from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    sector: Mapped[str] = mapped_column(String(128), index=True)
    industry: Mapped[str] = mapped_column(String(128), index=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    pe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    eps: Mapped[float | None] = mapped_column(Float, nullable=True)
    revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    debt_to_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    dividend_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PriceBar(Base):
    __tablename__ = "price_bars"
    __table_args__ = (UniqueConstraint("ticker", "bar_date", name="uq_ticker_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    bar_date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)


class QuoteSnapshot(Base):
    __tablename__ = "quote_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    price: Mapped[float] = mapped_column(Float)
    change: Mapped[float] = mapped_column(Float)
    change_pct: Mapped[float] = mapped_column(Float)
    previous_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    label: Mapped[str] = mapped_column(String(64), default="Live")
    session_state: Mapped[str] = mapped_column(String(32), default="open")
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class CompanyRelationship(Base):
    __tablename__ = "company_relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_ticker: Mapped[str] = mapped_column(String(16), index=True)
    target_ticker: Mapped[str] = mapped_column(String(16), index=True)
    relationship_type: Mapped[str] = mapped_column(String(64))  # supplier|customer|competitor|partner
    plain_english: Mapped[str] = mapped_column(Text)


class AICache(Base):
    __tablename__ = "ai_cache"
    __table_args__ = (UniqueConstraint("cache_key", name="uq_ai_cache_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(512), index=True)
    kind: Mapped[str] = mapped_column(String(64))
    ticker: Mapped[str | None] = mapped_column(String(16), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class MacroObservation(Base):
    __tablename__ = "macro_observations"
    __table_args__ = (UniqueConstraint("series_id", "obs_date", name="uq_macro_series_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[str] = mapped_column(String(64), index=True)
    obs_date: Mapped[date] = mapped_column(Date)
    value: Mapped[float] = mapped_column(Float)


class EconomicEvent(Base):
    __tablename__ = "economic_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(64))
    plain_english: Mapped[str] = mapped_column(Text)
