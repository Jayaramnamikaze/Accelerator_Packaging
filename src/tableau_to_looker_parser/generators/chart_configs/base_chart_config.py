"""
Base abstract class for chart configuration generators.

Defines the interface that all chart configuration classes must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any


class BaseChartConfig(ABC):
    """Abstract base class for chart configuration generators."""

    def __init__(self):
        """Initialize base chart configuration."""
        self.supported_chart_types = self._get_supported_chart_types()

    @abstractmethod
    def _get_supported_chart_types(self) -> List[str]:
        """Return list of chart types supported by this configuration class."""
        pass

    @abstractmethod
    def get_visualization_type(self, tableau_chart_type: str) -> str:
        """
        Map Tableau chart type to LookML visualization type.

        Args:
            tableau_chart_type: Chart type from Tableau (e.g., 'bar', 'donut', 'heatmap')

        Returns:
            LookML visualization type (e.g., 'looker_column', 'tableau_to_looker::echarts_visualization_prod')
        """
        pass

    @abstractmethod
    def generate_chart_config(
        self,
        worksheet,
        fields: List[str],
        explore_name: str,
        color_palettes: Dict = None,
        field_encodings: Dict = None,
    ) -> Dict[str, Any]:
        """
        Generate chart-specific configuration dictionary.

        Args:
            worksheet: Worksheet schema object with visualization config
            fields: List of field references for the chart
            explore_name: Name of the explore being used
            color_palettes: Optional Tableau color palettes extracted from XML
            field_encodings: Optional Tableau field encodings extracted from XML

        Returns:
            Dictionary of chart-specific configuration options
        """
        pass

    def can_handle_chart_type(self, chart_type: str) -> bool:
        """Check if this configuration class can handle the given chart type."""
        return chart_type.lower() in [t.lower() for t in self.supported_chart_types]

    def generate_pivots(
        self, fields: List[str], explore_name: str, pivot_type: str = "auto"
    ) -> List[str]:
        """
        Generate pivot configuration for charts that need them.

        Args:
            fields: List of field references
            explore_name: Name of the explore
            pivot_type: Type of pivot needed ('date', 'dimension', 'auto')

        Returns:
            List of field references to use as pivots
        """
        pivots = []

        for field in fields:
            field_name = field.split(".")[-1] if "." in field else field

            if pivot_type == "date" or pivot_type == "auto":
                # Add date/time fields as pivots
                if any(
                    keyword in field_name.lower()
                    for keyword in ["date", "time", "day", "hour", "month", "year"]
                ):
                    pivots.append(field)

            if pivot_type == "dimension" or pivot_type == "auto":
                # Add dimension fields as pivots (exclude measures)
                if not any(
                    prefix in field_name.lower()
                    for prefix in ["total_", "avg_", "count_", "sum_", "min_", "max_"]
                ):
                    pivots.append(field)

        return pivots

    def generate_filters_config(self, worksheet, explore_name: str) -> Dict[str, str]:
        """Generate filters configuration from worksheet."""
        filters = {}

        if hasattr(worksheet, "filters") and worksheet.filters:
            for filter_config in worksheet.filters:
                field_name = filter_config.get("field", "").strip("[]")
                filter_value = filter_config.get("value", "")
                filter_key = f"{explore_name}.{field_name}"
                filters[filter_key] = filter_value

        return filters

    def generate_sorts_config(self, worksheet, explore_name: str) -> List[str]:
        """Generate sorts configuration from worksheet."""
        sorts = []

        if hasattr(worksheet, "sorting") and worksheet.sorting:
            for sort_config in worksheet.sorting:
                field_name = sort_config.get("field", "").strip("[]")
                direction = sort_config.get("direction", "ASC").lower()
                sort_field = f"{explore_name}.{field_name}"
                sorts.append(f"{sort_field} {direction}")

        return sorts

    def get_field_display_name(self, field: str) -> str:
        """Convert field name to display-friendly name."""
        if not field:
            return ""

        # Remove explore prefix (e.g., "orders.total_sales" -> "total_sales")
        if "." in field:
            field = field.split(".")[-1]

        # Remove aggregation prefix and title case
        field = (
            field.replace("total_", "")
            .replace("sum_", "")
            .replace("avg_", "")
            .replace("count_", "")
            .replace("min_", "")
            .replace("max_", "")
        )
        return field.replace("_", " ").title()
