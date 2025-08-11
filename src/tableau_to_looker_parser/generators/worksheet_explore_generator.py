"""
Worksheet-based Explore Generator.

Generates LookML explores based on Tableau worksheet field usage patterns,
following the standard architecture: JSON → Generator → LookML.
"""

from typing import Dict, List, Optional
import logging

from .base_generator import BaseGenerator

logger = logging.getLogger(__name__)


class WorksheetExploreGenerator(BaseGenerator):
    """Generate explores from worksheet field usage patterns."""

    def generate_explores(self, migration_data: Dict) -> List[Dict]:
        """
        Generate explore definitions from worksheet data.

        Args:
            migration_data: Processed JSON data containing worksheets

        Returns:
            List of explore definitions ready for model template
        """
        explores = []
        worksheets = migration_data.get("worksheets", [])

        if not worksheets:
            logger.info("No worksheets found for explore generation")
            return explores

        # Get base table for explore foundation
        base_table = self._get_base_table(migration_data)
        if not base_table:
            logger.warning("No base table found for explore generation")
            return explores

        # Create one explore per worksheet
        for worksheet in worksheets:
            try:
                explore = self._create_explore_from_worksheet(worksheet, base_table)
                if explore:
                    explores.append(explore)
            except Exception as e:
                logger.error(
                    f"Failed to generate explore for worksheet {worksheet.get('name')}: {e}"
                )
                continue

        logger.info(f"Generated {len(explores)} worksheet-based explores")
        return explores

    def _get_base_table(self, migration_data: Dict) -> Optional[Dict]:
        """Get the primary table to base explores on."""
        tables = migration_data.get("tables", [])
        return tables[0] if tables else None

    def _create_explore_from_worksheet(
        self, worksheet: Dict, base_table: Dict
    ) -> Optional[Dict]:
        """
        Create a single explore definition from worksheet data.

        Args:
            worksheet: Worksheet JSON data with field usage
            base_table: Base table information

        Returns:
            Explore definition dictionary
        """
        explore_name = worksheet.get("clean_name")
        if not explore_name:
            return None

        # Extract field usage from worksheet
        dimensions = self._extract_dimensions(worksheet)
        measures = self._extract_measures(worksheet)

        # Build explore definition
        explore = {
            "name": explore_name,
            "label": worksheet.get("name", "").replace("_", " ").title(),
            "from": base_table["name"].lower(),
            "description": f"Analysis view for {worksheet.get('name', explore_name)}",
            "dimensions": dimensions,
            "measures": measures,
            "chart_type": worksheet.get("visualization", {}).get("chart_type", "bar"),
            "is_dual_axis": worksheet.get("visualization", {}).get(
                "is_dual_axis", False
            ),
        }

        return explore

    def _extract_dimensions(self, worksheet: Dict) -> List[str]:
        """Extract dimension field names from worksheet."""
        dimensions = []

        fields = worksheet.get("fields", [])
        for field in fields:
            if field.get("role") == "dimension":
                field_name = field.get("name")
                if field_name and field_name not in dimensions:
                    dimensions.append(field_name)

        return dimensions

    def _extract_measures(self, worksheet: Dict) -> List[str]:
        """Extract measure field names from worksheet."""
        measures = []

        fields = worksheet.get("fields", [])
        for field in fields:
            if field.get("role") == "measure":
                field_name = field.get("name")
                if field_name and field_name not in measures:
                    measures.append(field_name)

        return measures
