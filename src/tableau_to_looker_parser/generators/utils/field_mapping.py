"""
Field mapping utilities for dashboard generation.

Handles conversion of Tableau field references to LookML field references,
including aggregation type mapping and field validation.
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class FieldMapper:
    """Utility class for mapping Tableau fields to LookML field references."""

    def __init__(self):
        """Initialize field mapper."""
        self.aggregation_mapping = {
            "sum": "total_",
            "avg": "avg_",
            "count": "count_",
            "countd": "count_",  # Count distinct maps to count in LookML
            "min": "min_",
            "max": "max_",
        }

    def build_fields_from_worksheet(self, worksheet, explore_name: str) -> List[str]:
        """
        Build fields array from worksheet fields for LookML dashboard.

        Args:
            worksheet: Worksheet schema object
            explore_name: Name of the explore to reference

        Returns:
            List of LookML field references (e.g., ["orders.category", "orders.total_sales"])
        """
        fields = []

        # Get fields from the worksheet schema
        worksheet_fields = worksheet.fields if hasattr(worksheet, "fields") else []

        for field in worksheet_fields:
            # Skip internal fields
            if self._is_internal_field(field):
                field_name = self._get_field_name(field)
                logger.debug(f"Skipping internal field: {field_name}")
                continue

            # Convert to explore.field format
            field_name = self._get_field_name(field)
            if field_name:
                # Add proper measure aggregation types for dashboard fields
                aggregated_field_name = self._add_measure_aggregation_type(
                    field_name, field
                )
                fields.append(f"{explore_name.lower()}.{aggregated_field_name}")

        return fields

    def _is_internal_field(self, field) -> bool:
        """Check if field is internal and should be skipped."""
        if hasattr(field, "is_internal"):
            return field.is_internal
        elif hasattr(field, "get"):
            return field.get("is_internal", False)
        return False

    def _get_field_name(self, field) -> str:
        """Extract field name from field object."""
        if hasattr(field, "name"):
            return field.name
        elif hasattr(field, "get"):
            return field.get("name", "")
        return ""

    def _add_measure_aggregation_type(self, field_name: str, field) -> str:
        """
        Add proper aggregation type to measure field names for dashboard references.

        Args:
            field_name: Base field name
            field: Field object with type and aggregation info

        Returns:
            Field name with aggregation prefix for measures, unchanged for dimensions
        """
        # Get field type and aggregation from field object
        field_type = self._get_field_type(field)
        field_aggregation = self._get_field_aggregation(field)

        # For date/time dimensions, don't add measure prefixes - keep as dimensions
        field_lower = field_name.lower()
        if any(
            keyword in field_lower
            for keyword in ["rpt_dt", "rpt_time", "date", "time", "hour", "day"]
        ):
            # These should remain as dimensions in the view
            return field_name

        # Check if this is a measure field
        if field_type == "measure":
            if field_aggregation:
                aggregation_lower = field_aggregation.lower()

                # Map aggregation types to measure prefixes
                prefix = self.aggregation_mapping.get(aggregation_lower, "total_")
                return f"{prefix}{field_lower}"

            # Fallback for measures without aggregation info
            return f"total_{field_lower}"

        # Return dimension fields as-is
        return field_name

    def _get_field_type(self, field) -> str:
        """Extract field type from field object."""
        if hasattr(field, "type"):
            return field.type
        elif hasattr(field, "role"):
            return field.role
        elif hasattr(field, "get"):
            return field.get("type", field.get("role", "dimension"))
        return "dimension"

    def _get_field_aggregation(self, field) -> str:
        """Extract field aggregation from field object."""
        if hasattr(field, "aggregation"):
            return field.aggregation
        elif hasattr(field, "get"):
            return field.get("aggregation", "")
        return ""

    def get_fill_fields_from_worksheet(self, worksheet, explore_name: str) -> List[str]:
        """
        Get fill_fields for time-based visualizations.

        Args:
            worksheet: Worksheet schema object
            explore_name: Name of the explore

        Returns:
            List of date/time fields to use for filling
        """
        fill_fields = []

        # Get fields from the worksheet schema
        worksheet_fields = worksheet.fields if hasattr(worksheet, "fields") else []

        # Look for date/time fields that should be filled
        for field in worksheet_fields:
            field_name = self._get_field_name(field)
            datatype = self._get_field_datatype(field)

            # Check if field is a date/time field or has date-like name
            is_date_field = datatype in ["date", "datetime"] or any(
                keyword in field_name.lower()
                for keyword in ["date", "time", "year", "month", "day", "quarter"]
            )

            if is_date_field:
                fill_fields.append(f"{explore_name.lower()}.{field_name}")

        return fill_fields

    def _get_field_datatype(self, field) -> str:
        """Extract field datatype from field object."""
        if hasattr(field, "datatype"):
            return field.datatype
        elif hasattr(field, "get"):
            return field.get("datatype", "")
        return ""

    def build_filters_from_worksheet(
        self, worksheet, explore_name: str
    ) -> Dict[str, str]:
        """
        Build filters dictionary from worksheet filters.

        Args:
            worksheet: Worksheet schema object
            explore_name: Name of the explore

        Returns:
            Dictionary of filter configurations
        """
        filters = {}

        if hasattr(worksheet, "filters") and worksheet.filters:
            for filter_config in worksheet.filters:
                field_name = filter_config.get("field", "").strip("[]")
                filter_value = filter_config.get("value", "")
                # Convert to explore.field format
                filter_key = f"{explore_name.lower()}.{field_name}"
                filters[filter_key] = filter_value

        return filters

    def build_sorts_from_worksheet(self, worksheet, explore_name: str) -> List[str]:
        """
        Build sorts array from worksheet sorting configuration.

        Args:
            worksheet: Worksheet schema object
            explore_name: Name of the explore

        Returns:
            List of sort configurations
        """
        sorts = []

        if hasattr(worksheet, "sorting") and worksheet.sorting:
            for sort_config in worksheet.sorting:
                field_name = sort_config.get("field", "").strip("[]")
                direction = sort_config.get("direction", "ASC").lower()
                # Convert to explore.field format
                sort_field = f"{explore_name.lower()}.{field_name}"
                sorts.append(f"{sort_field} {direction}")

        return sorts
