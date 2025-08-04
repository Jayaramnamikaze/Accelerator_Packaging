"""
Dashboard LookML generator for Tableau to LookML migration.

Converts Tableau dashboard schemas into LookML dashboard files with proper
element positioning, filters, and visualization configurations.
"""

from typing import Dict, List, Optional
import logging
from datetime import datetime

from .base_generator import BaseGenerator
from ..models.dashboard_models import DashboardSchema, DashboardElement, ElementType

logger = logging.getLogger(__name__)


class DashboardGenerator(BaseGenerator):
    """Generate LookML dashboard files from Tableau dashboard schemas."""

    def __init__(self, template_dir: Optional[str] = None):
        """Initialize dashboard generator with template engine."""
        super().__init__(template_dir)
        self.dashboard_extension = ".dashboard"

    def generate(self, migration_data: Dict, output_dir: str) -> List[str]:
        """
        Generate dashboard.lkml files from migration data.

        Args:
            migration_data: Migration data containing dashboards
            output_dir: Output directory for generated files

        Returns:
            List of generated file paths
        """
        generated_files = []
        dashboards = migration_data.get("dashboards", [])

        if not dashboards:
            logger.info("No dashboards found in migration data")
            return generated_files

        for dashboard_data in dashboards:
            try:
                # Convert to schema if needed
                if isinstance(dashboard_data, dict):
                    dashboard = DashboardSchema(**dashboard_data)
                else:
                    dashboard = dashboard_data

                # Generate dashboard content
                dashboard_content = self._generate_dashboard_content(
                    dashboard, migration_data
                )

                # Write dashboard file
                file_path = self._write_dashboard_file(
                    dashboard.clean_name, dashboard_content, output_dir
                )
                generated_files.append(file_path)

            except Exception as e:
                logger.error(
                    f"Failed to generate dashboard {dashboard_data.get('name', 'unknown')}: {e}"
                )
                continue

        logger.info(f"Generated {len(generated_files)} dashboard files")
        return generated_files

    def _generate_dashboard_content(
        self, dashboard: DashboardSchema, migration_data: Dict
    ) -> str:
        """Generate LookML dashboard content from schema."""

        # Convert dashboard elements to LookML format
        elements = self._convert_elements_to_lookml(dashboard.elements, migration_data)

        # Convert global filters
        filters = self._convert_filters_to_lookml(dashboard.global_filters)

        # Prepare template context
        context = {
            "dashboard_name": dashboard.clean_name,
            "title": dashboard.title,
            "source_dashboard_name": dashboard.name,
            "generation_timestamp": datetime.now().isoformat(),
            "description": getattr(dashboard, "description", ""),
            "layout_type": dashboard.layout_type,
            "elements": elements,
            "filters": filters,
            "cross_filter_enabled": dashboard.cross_filter_enabled,
            "preferred_viewer": "dashboards-next",  # Default to modern viewer
            "preferred_slug": getattr(dashboard, "preferred_slug", None),
            # Additional LookML dashboard properties
            "auto_run": True,
            "refresh_interval": None,
            "shared": True,
            "show_filters_bar": True,
            "show_title": True,
            "background_color": "#ffffff",
            "load_configuration": "wait",
        }

        return self.template_engine.render_template("dashboard.j2", context)

    def _convert_elements_to_lookml(
        self, elements: List[DashboardElement], migration_data: Dict
    ) -> List[Dict]:
        """Convert dashboard elements to LookML element format."""
        lookml_elements = []

        for element in elements:
            try:
                if element.element_type == ElementType.WORKSHEET:
                    lookml_element = self._convert_worksheet_element(
                        element, migration_data
                    )
                elif element.element_type == ElementType.FILTER:
                    lookml_element = self._convert_filter_element(element)
                elif element.element_type == ElementType.PARAMETER:
                    lookml_element = self._convert_parameter_element(element)
                elif element.element_type == ElementType.TEXT:
                    lookml_element = self._convert_text_element(element)
                else:
                    logger.warning(f"Unsupported element type: {element.element_type}")
                    continue

                if lookml_element:
                    lookml_elements.append(lookml_element)

            except Exception as e:
                logger.error(f"Failed to convert element {element.element_id}: {e}")
                continue

        return lookml_elements

    def _convert_worksheet_element(
        self, element: DashboardElement, migration_data: Dict
    ) -> Optional[Dict]:
        """Convert worksheet element to LookML format."""
        if not element.worksheet:
            logger.warning(
                f"Worksheet element {element.element_id} has no worksheet data"
            )
            return None

        worksheet = element.worksheet

        # Determine chart type from worksheet visualization
        chart_type = self._map_chart_type_to_lookml(worksheet.visualization.chart_type)

        # Get model and explore name
        model_name = migration_data.get("metadata", {}).get(
            "project_name", "tableau_migration"
        )
        # Use main table explore instead of worksheet-specific explores
        main_table = migration_data.get("tables", [{}])[0]
        explore_name = (
            main_table.get("name", "main_table") if main_table else "main_table"
        )

        # Build fields array from worksheet field usage
        fields = self._build_fields_from_worksheet(worksheet, explore_name)

        # Use existing dual-axis detection from visualization config
        is_dual_axis = getattr(worksheet.visualization, "is_dual_axis", False)

        # Build filters from worksheet
        filters = self._build_filters_from_worksheet(worksheet)

        # Build sorts from worksheet
        sorts = self._build_sorts_from_worksheet(worksheet)

        # Create LookML element matching the YAML format
        lookml_element = {
            "title": worksheet.name.replace("_", " ").title(),
            "name": worksheet.clean_name,
            "model": model_name,
            "explore": explore_name,
            "type": chart_type,
            "layout": self._calculate_responsive_layout(element, migration_data),
            "listen": {},  # Will be populated with filter connections
        }

        # Add optional fields
        if fields:
            lookml_element["fields"] = fields

        if filters:
            lookml_element["filters"] = filters

        if sorts:
            lookml_element["sorts"] = sorts

        # Add default limits
        lookml_element["limit"] = 500
        lookml_element["column_limit"] = 50

        # Add fill_fields for time-based charts
        fill_fields = self._get_fill_fields_from_worksheet(worksheet)
        if fill_fields:
            lookml_element["fill_fields"] = fill_fields

        # Add dual-axis configuration if detected
        if is_dual_axis or self._is_dual_axis_chart_type(chart_type):
            dual_axis_config = self._generate_dual_axis_config(fields, explore_name)
            lookml_element.update(dual_axis_config)

        # Note: Visualization options are handled in the explore/view definitions
        # LookML dashboards should not contain detailed viz options

        return lookml_element

    def _convert_filter_element(self, element: DashboardElement) -> Optional[Dict]:
        """Convert filter element to LookML format (usually handled as dashboard filters)."""
        # Filter elements are typically converted to dashboard-level filters
        # Rather than individual elements, but we can create a text element as placeholder
        return {
            "name": f"filter_{element.element_id}",
            "title": f"Filter: {element.filter_config.get('field', 'Unknown')}",
            "type": "text",
            "layout": {
                "column": int(element.position.x * 24),
                "row": int(element.position.y * 20),
                "width": max(1, int(element.position.width * 24)),
                "height": 1,  # Filters are typically 1 row high
            },
            "note": f"Filter element: {element.filter_config.get('field', 'Unknown')}",
        }

    def _convert_parameter_element(self, element: DashboardElement) -> Optional[Dict]:
        """Convert parameter element to LookML format."""
        return {
            "name": f"parameter_{element.element_id}",
            "title": f"Parameter: {element.parameter_config.get('name', 'Unknown')}",
            "type": "text",
            "layout": {
                "column": int(element.position.x * 24),
                "row": int(element.position.y * 20),
                "width": max(1, int(element.position.width * 24)),
                "height": 1,
            },
            "note": f"Parameter element: {element.parameter_config.get('name', 'Unknown')}",
        }

    def _convert_text_element(self, element: DashboardElement) -> Optional[Dict]:
        """Convert text element to LookML format."""
        return {
            "name": f"text_{element.element_id}",
            "title": "Text Element",
            "type": "text",
            "layout": {
                "column": int(element.position.x * 24),
                "row": int(element.position.y * 20),
                "width": max(1, int(element.position.width * 24)),
                "height": max(1, int(element.position.height * 10)),
            },
            "note": element.text_content or "Text element",
        }

    def _convert_filters_to_lookml(self, global_filters: List) -> List[Dict]:
        """Convert global dashboard filters to LookML YAML format."""
        lookml_filters = []

        for filter_obj in global_filters:
            lookml_filter = {
                "name": filter_obj.name,
                "title": filter_obj.title,
                "type": filter_obj.filter_type,
                "default_value": filter_obj.default_value or "",
                "allow_multiple_values": True,
                "required": False,
                "ui_config": {"type": "advanced", "display": "popover", "options": []},
                "model": filter_obj.explore,  # Assuming explore name is the model
                "explore": filter_obj.explore,
                "listens_to_filters": [],
                "field": filter_obj.field,
            }
            lookml_filters.append(lookml_filter)

        return lookml_filters

    def _build_fields_from_worksheet(self, worksheet, explore_name: str) -> List[str]:
        """Build fields array from worksheet fields."""
        fields = []

        # Get fields from the worksheet schema
        worksheet_fields = worksheet.fields if hasattr(worksheet, "fields") else []

        for field in worksheet_fields:
            # Skip internal fields - handle both dict and object forms
            is_internal = False
            if hasattr(field, "is_internal"):
                is_internal = field.is_internal
            elif hasattr(field, "get"):
                is_internal = field.get("is_internal", False)

            if is_internal:
                field_name_for_log = getattr(field, "name", None) or (
                    field.get("name") if hasattr(field, "get") else "unknown"
                )
                logger.debug(f"Skipping internal field: {field_name_for_log}")
                continue

            # Convert to explore.field format using main explore (lowercase)
            field_name = field.name if hasattr(field, "name") else field.get("name", "")
            if field_name:
                # Add proper measure aggregation types for dashboard fields
                aggregated_field_name = self._add_measure_aggregation_type(
                    field_name, field
                )
                fields.append(f"{explore_name.lower()}.{aggregated_field_name}")

        return fields

    def _add_measure_aggregation_type(self, field_name: str, field) -> str:
        """Add proper aggregation type to measure field names for dashboard references."""
        # Get field type from field object if available
        field_type = getattr(field, "type", None) or getattr(field, "role", "dimension")

        # Check if this is a measure field
        if field_type == "measure" or field_name.lower() in [
            "sales",
            "profit",
            "quantity",
            "discount",
        ]:
            # Map common measure names to appropriate aggregation types
            measure_mappings = {
                "sales": "total_sales",
                "profit": "total_profit",
                "quantity": "total_quantity",
                "discount": "avg_discount",
                "revenue": "total_revenue",
                "amount": "total_amount",
                "price": "avg_price",
                "cost": "total_cost",
            }

            field_lower = field_name.lower()

            # Use explicit mapping if available
            if field_lower in measure_mappings:
                return measure_mappings[field_lower]

            # For other numeric measures, default to total/sum
            if any(
                keyword in field_lower
                for keyword in ["sales", "profit", "revenue", "amount", "cost"]
            ):
                return f"total_{field_name.lower()}"
            elif any(keyword in field_lower for keyword in ["count", "number"]):
                return f"count_{field_name.lower()}"
            elif any(
                keyword in field_lower
                for keyword in ["rate", "percent", "avg", "average"]
            ):
                return f"avg_{field_name.lower()}"
            else:
                return f"sum_{field_name.lower()}"

        # Return dimension fields as-is
        return field_name

    def _build_filters_from_worksheet(self, worksheet) -> Dict[str, str]:
        """Build filters dictionary from worksheet filters."""
        filters = {}

        if hasattr(worksheet, "filters") and worksheet.filters:
            for filter_config in worksheet.filters:
                field_name = filter_config.get("field", "").strip("[]")
                filter_value = filter_config.get("value", "")
                # Convert to explore.field format
                filter_key = f"{worksheet.clean_name}.{field_name}"
                filters[filter_key] = filter_value

        return filters

    def _build_sorts_from_worksheet(self, worksheet) -> List[str]:
        """Build sorts array from worksheet sorting configuration."""
        sorts = []

        if hasattr(worksheet, "sorting") and worksheet.sorting:
            for sort_config in worksheet.sorting:
                field_name = sort_config.get("field", "").strip("[]")
                direction = sort_config.get("direction", "ASC").lower()
                # Convert to explore.field format
                sort_field = f"{worksheet.clean_name}.{field_name}"
                sorts.append(f"{sort_field} {direction}")

        return sorts

    def _get_fill_fields_from_worksheet(self, worksheet) -> List[str]:
        """Get fill_fields for time-based visualizations."""
        fill_fields = []

        # Get fields from the worksheet schema
        worksheet_fields = worksheet.fields if hasattr(worksheet, "fields") else []

        # Look for date/time fields that should be filled
        for field in worksheet_fields:
            field_name = field.name if hasattr(field, "name") else field.get("name", "")
            datatype = (
                field.datatype
                if hasattr(field, "datatype")
                else field.get("datatype", "")
            )

            # Check if field is a date/time field or has date-like name
            is_date_field = datatype in ["date", "datetime"] or any(
                keyword in field_name.lower()
                for keyword in ["date", "time", "year", "month", "day", "quarter"]
            )

            if is_date_field:
                fill_fields.append(f"{worksheet.clean_name}.{field_name}")

        return fill_fields

    def _map_chart_type_to_lookml(self, tableau_chart_type: str) -> str:
        """Map Tableau chart types to LookML visualization types."""
        chart_type_mapping = {
            "bar": "looker_column",
            "line": "looker_line",
            "area": "looker_area",
            "pie": "looker_pie",
            "scatter": "looker_scatter",
            "text": "single_value",
            "text_table": "looker_grid",  # Crosstab/pivot table
            "map": "looker_map",
            "table": "looker_grid",
            # Dual-axis charts use native Looker dual-axis support
            "bar_and_line": "looker_line",  # Line chart with dual-axis
            "bar_and_area": "looker_area",  # Area chart with dual-axis
            "line_and_bar": "looker_column",  # Column chart with dual-axis
            "unknown": "looker_column",  # Default fallback
        }

        return chart_type_mapping.get(tableau_chart_type.lower(), "looker_column")

    def _is_dual_axis_chart_type(self, chart_type: str) -> bool:
        """Check if chart type indicates dual-axis visualization."""
        dual_axis_types = [
            "bar_and_line",
            "bar_and_area",
            "line_and_bar",
            "bar_and_scatter",
            "line_and_area",
        ]
        return chart_type in dual_axis_types

    def _generate_dual_axis_config(self, fields: List[str], explore_name: str) -> Dict:
        """Generate y_axes configuration for dual-axis charts."""
        if not fields:
            return {}

        # Extract measure fields (those with aggregation prefixes)
        measure_fields = [
            f
            for f in fields
            if any(
                prefix in f.lower() for prefix in ["total_", "sum_", "avg_", "count_"]
            )
        ]

        if len(measure_fields) < 2:
            # Single measure, still add basic y_axes for consistency
            return {
                "y_axes": [
                    {
                        "label": "",
                        "orientation": "left",
                        "series": [
                            {
                                "axisId": measure_fields[0]
                                if measure_fields
                                else fields[0],
                                "id": measure_fields[0]
                                if measure_fields
                                else fields[0],
                                "name": self._get_field_display_name(
                                    measure_fields[0] if measure_fields else fields[0]
                                ),
                            }
                        ],
                        "showLabels": True,
                        "showValues": True,
                        "valueFormat": '0,"K"',
                        "unpinAxis": False,
                        "tickDensity": "default",
                        "type": "linear",
                    }
                ]
            }

        # Multiple measures - create dual-axis configuration
        series = []
        colors = ["#5C8BB6", "#ED9149", "#4E7599", "#D56339"]  # Color palette

        for i, field in enumerate(measure_fields[:4]):  # Limit to 4 measures
            series.append(
                {
                    "axisId": field,
                    "id": field,
                    "name": self._get_field_display_name(field),
                }
            )

        config = {
            "y_axes": [
                {
                    "label": "",
                    "orientation": "left",
                    "series": series,
                    "showLabels": True,
                    "showValues": True,
                    "valueFormat": '0,"K"',
                    "unpinAxis": False,
                    "tickDensity": "default",
                    "type": "linear",
                }
            ],
            "x_axis_gridlines": False,
            "y_axis_gridlines": False,
            "show_y_axis_labels": True,
            "show_y_axis_ticks": True,
            "y_axis_combined": True,
            "series_colors": {},
        }

        # Add series colors
        for i, field in enumerate(measure_fields[: len(colors)]):
            config["series_colors"][field] = colors[i]

        return config

    def _get_field_display_name(self, field: str) -> str:
        """Convert field name to display name."""
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
        )
        return field.replace("_", " ").title()

    def _extract_viz_options_from_worksheet(self, worksheet) -> Dict:
        """Extract comprehensive visualization options from worksheet configuration."""
        viz_options = {}
        chart_type = worksheet.visualization.chart_type.lower()

        # Common options for all chart types
        common_options = {
            "x_axis_gridlines": False,
            "y_axis_gridlines": False,
            "show_view_names": False,
            "show_y_axis_labels": True,
            "show_y_axis_ticks": True,
            "y_axis_tick_density": "default",
            "y_axis_tick_density_custom": 5,
            "show_x_axis_label": False,
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
            "x_axis_zoom": True,
            "y_axis_zoom": True,
            "show_null_points": True,
            "defaults_version": 1,
        }

        viz_options.update(common_options)

        # Chart-specific options
        if "line" in chart_type:
            viz_options.update(
                {
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
            )

        elif "area" in chart_type:
            viz_options.update(
                {
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
            )

        elif "single_value" in chart_type or chart_type == "text":
            viz_options.update(
                {
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
            )

        elif "bar" in chart_type or "column" in chart_type:
            viz_options.update(
                {
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
                    "color_application": "undefined",
                    "up_color": False,
                    "down_color": False,
                    "total_color": False,
                    "font_size": 12,
                    "hidden_pivots": {},
                }
            )

        elif "packed_bubble" in chart_type or "bubble" in chart_type:
            viz_options.update(
                {
                    "color_by_type": "gradient",
                    "toColor": ["#2A5783", "#ffed6f", "#EE7772"],
                    "value_labels": True,
                    "value_titles": True,
                    "font_size_value": "8",
                    "font_size_label": "10",
                    "label_value_format": "#,##0",
                    "label_color": ["#333333"],
                }
            )

        return viz_options

    def _calculate_responsive_layout(
        self, element: DashboardElement, migration_data: Dict
    ) -> Dict[str, int]:
        """
        Calculate responsive layout positioning based on Tableau layout type and element positioning.

        Handles different Tableau layout patterns:
        - layout-basic (free_form) → Direct coordinate translation
        - layout-flow horizontal (grid) → Optimized for horizontal flow
        - layout-flow vertical (newspaper) → Optimized for vertical stacking
        - Mixed flows (newspaper) → Complex grid positioning
        """
        # Get dashboard layout type from migration data
        dashboard_info = next(
            (
                d
                for d in migration_data.get("dashboards", [])
                if any(
                    e.get("element_id") == element.element_id
                    for e in d.get("elements", [])
                )
            ),
            {},
        )
        layout_type = dashboard_info.get("layout_type", "free_form")

        # Base position from normalized coordinates
        base_layout = {
            "row": max(0, int(element.position.y * 20)),
            "col": max(0, int(element.position.x * 24)),
            "width": max(1, int(element.position.width * 24)),
            "height": max(1, int(element.position.height * 20)),
        }

        # Apply layout-specific optimizations
        if layout_type == "newspaper":
            # Newspaper layout: Optimize for vertical stacking and readability
            return self._optimize_for_newspaper_layout(base_layout, element)
        elif layout_type == "grid":
            # Grid layout: Optimize for horizontal flow and alignment
            return self._optimize_for_grid_layout(base_layout, element)
        else:
            # free_form: Use direct translation with minimal adjustments
            return self._optimize_for_freeform_layout(base_layout, element)

    def _optimize_for_newspaper_layout(
        self, layout: Dict[str, int], element: DashboardElement
    ) -> Dict[str, int]:
        """Optimize positioning for newspaper-style layout (vertical stacking)."""
        # Newspaper layout works well with wider elements and vertical flow
        optimized = layout.copy()

        # Ensure minimum readable width
        if optimized["width"] < 6:
            optimized["width"] = 6

        # Ensure reasonable height for charts
        if optimized["height"] < 4:
            optimized["height"] = 4

        # Snap to newspaper-friendly grid (multiples of 4)
        optimized["col"] = (optimized["col"] // 4) * 4
        optimized["width"] = max(4, (optimized["width"] // 4) * 4)

        return optimized

    def _optimize_for_grid_layout(
        self, layout: Dict[str, int], element: DashboardElement
    ) -> Dict[str, int]:
        """Optimize positioning for grid layout (horizontal flow)."""
        # Grid layout works well with consistent sizing and alignment
        optimized = layout.copy()

        # Ensure elements fit well in horizontal flow
        if optimized["width"] < 3:
            optimized["width"] = 3

        # Align to grid boundaries (multiples of 3 for 24-column grid)
        optimized["col"] = (optimized["col"] // 3) * 3
        optimized["width"] = max(3, (optimized["width"] // 3) * 3)

        # Consistent heights for horizontal alignment
        if optimized["height"] < 3:
            optimized["height"] = 3

        return optimized

    def _optimize_for_freeform_layout(
        self, layout: Dict[str, int], element: DashboardElement
    ) -> Dict[str, int]:
        """Optimize positioning for free-form layout (absolute positioning)."""
        # Free-form: Minimal adjustments, preserve original proportions
        optimized = layout.copy()

        # Ensure minimum viable sizes
        optimized["width"] = max(1, optimized["width"])
        optimized["height"] = max(1, optimized["height"])

        # Ensure elements don't go off-screen
        if optimized["col"] + optimized["width"] > 24:
            optimized["col"] = max(0, 24 - optimized["width"])

        if optimized["row"] + optimized["height"] > 30:  # Assume max 30 rows
            optimized["row"] = max(0, 30 - optimized["height"])

        return optimized

    def _write_dashboard_file(
        self, dashboard_name: str, content: str, output_dir: str
    ) -> str:
        """Write dashboard content to file."""
        output_path = self._ensure_output_dir(output_dir)

        # Create dashboard filename - dashboards use .dashboard extension only
        filename = f"{dashboard_name}{self.dashboard_extension}"
        file_path = output_path / filename

        return self._write_file(content, file_path)
