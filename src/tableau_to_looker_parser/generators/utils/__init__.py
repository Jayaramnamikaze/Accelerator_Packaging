"""
Utility modules for dashboard generation.

Provides helper functions for field mapping, layout calculations,
and other common dashboard generation tasks.
"""

from .field_mapping import FieldMapper
from .layout_calculator import LayoutCalculator

__all__ = [
    "FieldMapper",
    "LayoutCalculator",
]
