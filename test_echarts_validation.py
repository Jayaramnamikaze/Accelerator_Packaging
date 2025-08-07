#!/usr/bin/env python3
"""
Validate that the ECharts configuration is generating the complete properties
that match the manually created dashboard.
"""

import sys
import os

sys.path.append("src")

from tableau_to_looker_parser.core.migration_engine import MigrationEngine
from tableau_to_looker_parser.generators.lookml_generator import LookMLGenerator


def validate_echarts_properties():
    """Test that generated dashboards contain ECharts-specific properties."""
    print("🧪 Validating ECharts Properties Generation")
    print("=" * 50)

    try:
        # Process Connected Devices dashboard
        engine = MigrationEngine(use_v2_parser=True)
        migration_data = engine.migrate_file(
            "connected_devices_dashboard/Intraday_Sales.twb", "test_validation_output"
        )

        # Check extracted styling information
        color_palettes = migration_data.get("color_palettes", {})
        field_encodings = migration_data.get("field_encodings", {})

        print(f"✅ Extracted {len(color_palettes)} color palettes:")
        for name, palette in color_palettes.items():
            print(f"   - {name}: {len(palette['colors'])} colors")

        print(f"✅ Extracted field encodings for {len(field_encodings)} worksheets")

        # Generate LookML files
        generator = LookMLGenerator()
        generated_files = generator.generate_project_files(
            migration_data, "test_validation_output"
        )

        dashboard_files = generated_files.get("dashboards", [])
        print(f"✅ Generated {len(dashboard_files)} dashboard files")

        # Validate one dashboard file in detail
        if dashboard_files:
            test_file = dashboard_files[0]  # Use first dashboard
            print(f"\n📄 Validating: {os.path.basename(test_file)}")

            with open(test_file, "r") as f:
                content = f.read()

            # Check for ECharts-specific properties
            echarts_properties = [
                "chartType:",
                "colorPalette:",
                "themeSelector:",
                "showTooltip:",
                "labelAlignment:",
                "showLegend:",
                "borderRadius:",
                "xAxisSeriesToggle:",
                "yAxisSeriesToggle:",
                "dimensionColor_",
            ]

            found_properties = []
            missing_properties = []

            for prop in echarts_properties:
                if prop in content:
                    found_properties.append(prop)
                else:
                    missing_properties.append(prop)

            print(f"✅ Found {len(found_properties)} ECharts properties:")
            for prop in found_properties:
                print(f"   - {prop}")

            if missing_properties:
                print(f"❌ Missing {len(missing_properties)} ECharts properties:")
                for prop in missing_properties:
                    print(f"   - {prop}")

            # Show sample of generated content
            print("\n📄 Sample generated content (first 30 lines):")
            print("-" * 40)
            lines = content.split("\n")
            for i, line in enumerate(lines[:30]):
                if any(prop.rstrip(":") in line for prop in echarts_properties):
                    print(f"👉 {i + 1:2d}: {line}")
                else:
                    print(f"   {i + 1:2d}: {line}")
            print("-" * 40)

            # Determine success
            if (
                len(found_properties) >= 5
            ):  # At least 5 ECharts properties should be present
                print("🎉 SUCCESS: ECharts configuration is being generated!")
                return True
            else:
                print("❌ FAILURE: Not enough ECharts properties found")
                return False
        else:
            print("❌ No dashboard files generated")
            return False

    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = validate_echarts_properties()
    sys.exit(0 if success else 1)
