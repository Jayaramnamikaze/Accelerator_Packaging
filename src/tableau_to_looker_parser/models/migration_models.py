"""
Complete migration result models for Tableau to LookML conversion.

Contains the top-level migration result that combines all data from phases 1-3:
- Data layer: connections, datasources, dimensions, measures, relationships
- Presentation layer: worksheets and dashboards
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from .worksheet_models import WorksheetSchema
from .dashboard_models import DashboardSchema


class MigrationStats(BaseModel):
    """Statistics about the migration process."""

    # Source file info
    source_file_size_mb: float = Field(..., description="Source file size in megabytes")
    tableau_version: str = Field(
        ..., description="Tableau version that created the file"
    )

    # Processing counts
    total_worksheets: int = Field(
        default=0, description="Number of worksheets processed"
    )
    total_dashboards: int = Field(
        default=0, description="Number of dashboards processed"
    )
    total_datasources: int = Field(
        default=0, description="Number of datasources processed"
    )
    total_dimensions: int = Field(
        default=0, description="Number of dimensions processed"
    )
    total_measures: int = Field(default=0, description="Number of measures processed")
    total_calculated_fields: int = Field(
        default=0, description="Number of calculated fields processed"
    )
    total_relationships: int = Field(
        default=0, description="Number of table relationships processed"
    )

    # Processing quality
    successful_worksheets: int = Field(
        default=0, description="Worksheets processed successfully"
    )
    successful_dashboards: int = Field(
        default=0, description="Dashboards processed successfully"
    )
    failed_elements: int = Field(
        default=0, description="Elements that failed to process"
    )

    # Performance metrics
    processing_time_seconds: float = Field(
        default=0.0, description="Total processing time"
    )
    memory_usage_mb: float = Field(
        default=0.0, description="Peak memory usage during processing"
    )

    # Confidence metrics
    average_confidence: float = Field(
        default=0.0, description="Average handler confidence across all elements"
    )
    low_confidence_elements: int = Field(
        default=0, description="Elements with confidence < 0.7"
    )


class MigrationResult(BaseModel):
    """
    Complete migration result containing all data from Tableau to LookML conversion.

    Self-contained with efficient access patterns - no cross-references or lookups needed.
    Combines data layer (Phase 1-2) with presentation layer (Phase 3).
    """

    # Migration metadata
    source_file: str = Field(..., description="Path to original Tableau file")
    migration_timestamp: datetime = Field(
        default_factory=datetime.now, description="When migration was performed"
    )
    migration_version: str = Field(default="3.0", description="Migration tool version")

    # Processing statistics
    stats: MigrationStats = Field(..., description="Migration processing statistics")

    # =========================================================================
    # DATA LAYER (Phase 1-2): Database connections, tables, fields, relationships
    # =========================================================================

    connections: List[Dict[str, Any]] = Field(
        default_factory=list, description="Database connection configurations"
    )

    datasources: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Data source definitions with table references",
    )

    dimensions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Dimension field definitions from all datasources",
    )

    measures: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Measure field definitions from all datasources",
    )

    calculated_fields: List[Dict[str, Any]] = Field(
        default_factory=list, description="Calculated field definitions with formulas"
    )

    relationships: List[Dict[str, Any]] = Field(
        default_factory=list, description="Table relationships and join conditions"
    )

    # =========================================================================
    # PRESENTATION LAYER (Phase 3): Worksheets and dashboards with positioning
    # =========================================================================

    worksheets: List[WorksheetSchema] = Field(
        default_factory=list,
        description="Complete worksheet definitions with field usage and dashboard placements",
    )

    dashboards: List[DashboardSchema] = Field(
        default_factory=list,
        description="Complete dashboard definitions with element positioning",
    )

    # =========================================================================
    # CROSS-REFERENCES: Optional indexes for large datasets (built on demand)
    # =========================================================================

    _worksheet_index: Dict[str, WorksheetSchema] = Field(
        default_factory=dict,
        description="Worksheet name -> WorksheetSchema index for O(1) lookups",
    )

    _dashboard_index: Dict[str, DashboardSchema] = Field(
        default_factory=dict,
        description="Dashboard name -> DashboardSchema index for O(1) lookups",
    )

    _datasource_worksheet_map: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Datasource ID -> list of worksheet names using it",
    )

    # =========================================================================
    # ERROR TRACKING
    # =========================================================================

    processing_errors: List[str] = Field(
        default_factory=list, description="Any errors encountered during migration"
    )

    warnings: List[str] = Field(
        default_factory=list, description="Non-fatal warnings during migration"
    )

    # =========================================================================
    # EXTENSIBILITY
    # =========================================================================

    custom_data: Dict[str, Any] = Field(
        default_factory=dict, description="Custom data for future extensions"
    )

    # =========================================================================
    # PERFORMANCE METHODS: Build indexes for faster lookups in large datasets
    # =========================================================================

    def build_indexes(self) -> None:
        """Build indexes for O(1) lookups. Call this for large datasets."""
        # Worksheet index
        self._worksheet_index = {ws.name: ws for ws in self.worksheets}

        # Dashboard index
        self._dashboard_index = {db.name: db for db in self.dashboards}

        # Datasource -> worksheet mapping
        self._datasource_worksheet_map = {}
        for ws in self.worksheets:
            if ws.datasource_id not in self._datasource_worksheet_map:
                self._datasource_worksheet_map[ws.datasource_id] = []
            self._datasource_worksheet_map[ws.datasource_id].append(ws.name)

    # =========================================================================
    # CONVENIENCE METHODS: Fast access without lookups
    # =========================================================================

    def get_worksheet(self, name: str) -> Optional[WorksheetSchema]:
        """Get worksheet by name. O(1) if indexed, O(n) if not."""
        if self._worksheet_index:
            return self._worksheet_index.get(name)
        return next((ws for ws in self.worksheets if ws.name == name), None)

    def get_dashboard(self, name: str) -> Optional[DashboardSchema]:
        """Get dashboard by name. O(1) if indexed, O(n) if not."""
        if self._dashboard_index:
            return self._dashboard_index.get(name)
        return next((db for db in self.dashboards if db.name == name), None)

    def get_worksheets_by_datasource(self, datasource_id: str) -> List[WorksheetSchema]:
        """Get all worksheets using a specific datasource."""
        if self._datasource_worksheet_map:
            worksheet_names = self._datasource_worksheet_map.get(datasource_id, [])
            return [
                self.get_worksheet(name)
                for name in worksheet_names
                if self.get_worksheet(name)
            ]

        return [ws for ws in self.worksheets if ws.datasource_id == datasource_id]

    def get_dashboards_using_worksheet(
        self, worksheet_name: str
    ) -> List[DashboardSchema]:
        """Get all dashboards that contain a specific worksheet."""
        result = []
        for dashboard in self.dashboards:
            if worksheet_name in dashboard.get_worksheet_names():
                result.append(dashboard)
        return result

    def get_all_field_names(self) -> Dict[str, List[str]]:
        """Get all unique field names used across worksheets, grouped by type."""
        all_dimensions = set()
        all_measures = set()

        for worksheet in self.worksheets:
            for field in worksheet.fields:
                if field.role == "dimension":
                    all_dimensions.add(field.name)
                elif field.role == "measure":
                    all_measures.add(field.name)

        return {
            "dimensions": sorted(list(all_dimensions)),
            "measures": sorted(list(all_measures)),
        }

    def calculate_summary_stats(self) -> None:
        """Calculate and update migration statistics."""
        self.stats.total_worksheets = len(self.worksheets)
        self.stats.total_dashboards = len(self.dashboards)
        self.stats.total_datasources = len(self.datasources)
        self.stats.total_dimensions = len(self.dimensions)
        self.stats.total_measures = len(self.measures)
        self.stats.total_calculated_fields = len(self.calculated_fields)
        self.stats.total_relationships = len(self.relationships)

        # Calculate quality metrics
        worksheet_confidences = [
            ws.confidence for ws in self.worksheets if ws.confidence > 0
        ]
        dashboard_confidences = [
            db.confidence for db in self.dashboards if db.confidence > 0
        ]

        all_confidences = worksheet_confidences + dashboard_confidences
        if all_confidences:
            self.stats.average_confidence = sum(all_confidences) / len(all_confidences)
            self.stats.low_confidence_elements = len(
                [c for c in all_confidences if c < 0.7]
            )

        self.stats.successful_worksheets = len(
            [ws for ws in self.worksheets if ws.confidence >= 0.7]
        )
        self.stats.successful_dashboards = len(
            [db for db in self.dashboards if db.confidence >= 0.7]
        )
        self.stats.failed_elements = len(self.processing_errors)
