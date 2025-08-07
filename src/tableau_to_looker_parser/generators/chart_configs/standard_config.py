"""
Standard Looker visualization configuration generator.

Handles configuration for native Looker chart types (looker_column, looker_line, etc.)
"""

from typing import Dict, List, Any
from .base_chart_config import BaseChartConfig


class StandardConfig(BaseChartConfig):
    """Configuration generator for standard Looker visualizations."""

    def _get_supported_chart_types(self) -> List[str]:
        """Return list of chart types supported by standard Looker configuration."""
        return [
            "bar",
            "line",
            "area",
            "pie",
            "scatter",
            "text",
            "table",
            "map",
            "bar_and_line",
            "bar_and_area",
            "line_and_bar",
        ]

    def get_visualization_type(self, tableau_chart_type: str) -> str:
        """Map Tableau chart type to standard Looker visualization type."""
        chart_type_mapping = {
            "bar": "looker_column",
            "line": "looker_line",
            "area": "looker_area",
            "pie": "looker_pie",
            "scatter": "looker_scatter",
            "text": "single_value",
            "table": "looker_grid",
            "text_table": "looker_grid",
            "map": "looker_map",
            # Dual-axis charts use native Looker dual-axis support
            "bar_and_line": "looker_line",  # Line chart with dual-axis
            "bar_and_area": "looker_area",  # Area chart with dual-axis
            "line_and_bar": "looker_column",  # Column chart with dual-axis
        }

        return chart_type_mapping.get(tableau_chart_type.lower(), "looker_column")

    def generate_chart_config(
        self,
        worksheet,
        fields: List[str],
        explore_name: str,
        color_palettes: Dict = None,
        field_encodings: Dict = None,
    ) -> Dict[str, Any]:
        """Generate standard Looker chart configuration."""
        chart_type = worksheet.visualization.chart_type.lower()

        # Base configuration
        config = self._get_base_looker_config()

        # Chart-specific configurations
        if "line" in chart_type:
            config.update(self._get_line_config())
        elif "area" in chart_type:
            config.update(self._get_area_config())
        elif "single_value" in chart_type or chart_type == "text":
            config.update(self._get_single_value_config())
        elif "bar" in chart_type or "column" in chart_type:
            config.update(self._get_bar_config())
        elif "grid" in chart_type or chart_type == "table":
            config.update(self._get_table_config())

        return config

    def _get_base_looker_config(self) -> Dict[str, Any]:
        """Get base configuration common to all standard Looker charts."""
        return {
            "x_axis_gridlines": False,
            "y_axis_gridlines": True,
            "show_y_axis_labels": True,
            "show_y_axis_ticks": True,
            "y_axis_tick_density": "default",
            "y_axis_tick_density_custom": 5,
            "show_x_axis_label": True,
            "show_x_axis_ticks": True,
            "y_axis_scale_mode": "linear",
            "x_axis_reversed": False,
            "y_axis_reversed": False,
            "plot_size_by_field": False,
            "trellis": "",
            "stacking": "",
            "limit_displayed_rows": False,
            "legend_position": "center",
            "point_style": "none",
            "show_value_labels": False,
            "label_density": 25,
            "x_axis_scale": "auto",
            "y_axis_combined": True,
            "ordering": "none",
            "show_null_labels": False,
            "show_totals_labels": False,
            "show_silhouette": False,
            "totals_color": "#808080",
            "defaults_version": 0,
        }

    def _get_line_config(self) -> Dict[str, Any]:
        """Configuration for line charts."""
        return {
            "interpolation": "linear",
            "y_axes": [
                {
                    "label": "",
                    "orientation": "left",
                    "showLabels": True,
                    "showValues": True,
                    "valueFormat": '0,"K"',
                    "unpinAxis": False,
                    "tickDensity": "default",
                    "tickDensityCustom": 5,
                    "type": "linear",
                }
            ],
        }

    def _get_area_config(self) -> Dict[str, Any]:
        """Configuration for area charts."""
        return {
            "interpolation": "linear",
            "color_application": {
                "collection_id": "sample-colours",
                "custom": {
                    "id": "custom-color-palette",
                    "label": "Custom",
                    "type": "discrete",
                },
                "options": {"steps": 5},
            },
            "y_axes": [
                {
                    "label": "",
                    "orientation": "left",
                    "showLabels": True,
                    "showValues": True,
                    "valueFormat": '0,"K"',
                    "unpinAxis": False,
                    "tickDensity": "default",
                    "tickDensityCustom": 5,
                    "type": "linear",
                }
            ],
            "hide_legend": False,
            "series_colors": {},
            "x_axis_datetime_label": "",
        }

    def _get_single_value_config(self) -> Dict[str, Any]:
        """Configuration for single value charts."""
        return {
            "custom_color_enabled": True,
            "show_single_value_title": True,
            "show_comparison": False,
            "comparison_type": "value",
            "comparison_reverse_colors": False,
            "show_comparison_label": True,
            "enable_conditional_formatting": False,
            "conditional_formatting_include_totals": False,
            "conditional_formatting_include_nulls": False,
            "single_value_title": "",
        }

    def _get_bar_config(self) -> Dict[str, Any]:
        """Configuration for bar/column charts."""
        return {
            "y_axes": [
                {
                    "label": "",
                    "orientation": "left",
                    "showLabels": True,
                    "showValues": True,
                    "valueFormat": '0, "K"',
                    "unpinAxis": False,
                    "tickDensity": "default",
                    "tickDensityCustom": 5,
                    "type": "linear",
                }
            ],
            "series_colors": {},
            "show_sql_query_menu_options": False,
        }

    def _get_table_config(self) -> Dict[str, Any]:
        """Configuration for table/grid charts."""
        return {
            "show_totals": True,
            "show_row_totals": True,
            "show_row_numbers": True,
            "transpose": False,
            "truncate_text": True,
            "truncate_header": False,
            "size_to_fit": True,
            "minimum_column_width": 75,
            "table_theme": "white",
            "enable_conditional_formatting": False,
            "header_text_alignment": "left",
            "header_font_size": "12",
            "rows_font_size": "12",
            "conditional_formatting_include_totals": False,
            "conditional_formatting_include_nulls": False,
            "hide_totals": False,
            "hide_row_totals": False,
        }
