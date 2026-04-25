"""Vehicle profile domain entity and DrivingStyle enum."""

from enum import StrEnum


class DrivingStyle(StrEnum):
    URBAN = "urban"
    MIXED = "mixed"
    HIGHWAY = "highway"
