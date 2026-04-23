"""SQLAlchemy declarative base for all ORM models."""

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    """Common base for ORM models. AsyncAttrs enables `awaitable_attrs.<rel>`."""
