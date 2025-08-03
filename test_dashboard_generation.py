#!/usr/bin/env python3
"""
Comprehensive test for LookML dashboard generation functionality.

Tests the complete pipeline from Tableau dashboard parsing to LookML dashboard generation,
using the Bar_charts.twb sample and validating against the sales_and_profit format.
"""

import sys
import os
import tempfile

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from tableau_to_looker_parser.core.migration_engine import MigrationEngine
from tableau_to_looker_parser.generators.lookml_generator import LookMLGenerator


def test_dashboard_generation():
    """Test complete dashboard generation pipeline."""
    print("=== Testing Dashboard Generation Pipeline ===\n")

    # Test file path
    test_file = "sample_twb_files/Bar_charts.twb"

    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False

    try:
        # Step 1: Parse Tableau file and extract dashboards
        print("1. Parsing Tableau file and extracting dashboards...")
        engine = MigrationEngine(use_v2_parser=True)
        migration_data = engine.migrate_file(test_file, "temp_output")

        # Check if dashboards were extracted
        dashboards = migration_data.get("dashboards", [])
        worksheets = migration_data.get("worksheets", [])

        print(f"   ✅ Extracted {len(dashboards)} dashboards")
        print(f"   ✅ Extracted {len(worksheets)} worksheets")

        if not dashboards:
            print("   ⚠️  No dashboards found in the file")
            return False

        # Display dashboard information
        for i, dashboard in enumerate(dashboards):
            print(f"   Dashboard {i + 1}: {dashboard.get('name', 'Unknown')}")
            print(f"     - Elements: {len(dashboard.get('elements', []))}")
            print(f"     - Canvas Size: {dashboard.get('canvas_size', {})}")
            print(f"     - Layout Type: {dashboard.get('layout_type', 'unknown')}")

        print()

        # Step 2: Generate LookML files including dashboards
        print("2. Generating LookML files...")
        generator = LookMLGenerator()

        with tempfile.TemporaryDirectory() as temp_dir:
            generated_files = generator.generate_project_files(migration_data, temp_dir)

            print(f"   ✅ Generated file types: {list(generated_files.keys())}")

            # Check if dashboard files were generated
            dashboard_files = generated_files.get("dashboards", [])
            if dashboard_files:
                print(f"   ✅ Generated {len(dashboard_files)} dashboard files")

                # Validate dashboard file content
                for dashboard_file in dashboard_files:
                    if os.path.exists(dashboard_file):
                        print(
                            f"   📄 Dashboard file: {os.path.basename(dashboard_file)}"
                        )

                        # Read and validate dashboard content
                        with open(dashboard_file, "r") as f:
                            dashboard_content = f.read()

                        # Basic validation
                        if validate_dashboard_content(dashboard_content):
                            print("      ✅ Valid LookML dashboard format")
                        else:
                            print("      ❌ Invalid LookML dashboard format")
                            return False

                        # Show sample content
                        print("      📝 Sample content (first 10 lines):")
                        lines = dashboard_content.split("\n")[:10]
                        for line in lines:
                            print(f"         {line}")
                        print("         ...")
                    else:
                        print(f"   ❌ Dashboard file not found: {dashboard_file}")
                        return False
            else:
                print("   ⚠️  No dashboard files generated")
                return False

        print()

        # Step 3: Validate generated structure matches expected format
        print("3. Validating dashboard structure...")

        # Load the first dashboard for detailed validation
        first_dashboard = dashboards[0]
        if validate_dashboard_structure(first_dashboard):
            print("   ✅ Dashboard structure validation passed")
        else:
            print("   ❌ Dashboard structure validation failed")
            return False

        print()
        print("🎉 Dashboard generation test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def validate_dashboard_content(content: str) -> bool:
    """Validate that the generated content matches LookML dashboard format."""
    required_elements = [
        "- dashboard:",
        "title:",
        "layout:",
        "elements:",
        "row:",
        "col:",
        "width:",
        "height:",
    ]

    for element in required_elements:
        if element not in content:
            print(f"      ❌ Missing required element: {element}")
            return False

    return True


def validate_dashboard_structure(dashboard: dict) -> bool:
    """Validate the dashboard data structure."""
    required_fields = ["name", "clean_name", "elements", "canvas_size"]

    for field in required_fields:
        if field not in dashboard:
            print(f"   ❌ Missing required field: {field}")
            return False

    # Validate elements structure
    elements = dashboard.get("elements", [])
    if not elements:
        print("   ⚠️  Dashboard has no elements")

    for i, element in enumerate(elements):
        required_element_fields = ["element_id", "element_type", "position"]
        for field in required_element_fields:
            if field not in element:
                print(f"   ❌ Element {i} missing required field: {field}")
                return False

        # Validate position structure
        position = element.get("position", {})
        required_position_fields = ["x", "y", "width", "height"]
        for field in required_position_fields:
            if field not in position:
                print(f"   ❌ Element {i} position missing field: {field}")
                return False

    return True


def test_template_rendering():
    """Test the dashboard template rendering with sample data."""
    print("=== Testing Dashboard Template Rendering ===\n")

    try:
        from tableau_to_looker_parser.generators.dashboard_generator import (
            DashboardGenerator,
        )
        from tableau_to_looker_parser.models.dashboard_models import (
            DashboardSchema,
            DashboardElement,
            ElementType,
        )
        from tableau_to_looker_parser.models.position_models import Position
        from tableau_to_looker_parser.models.worksheet_models import (
            WorksheetSchema,
            FieldReference,
            VisualizationConfig,
        )

        # Create sample dashboard data
        sample_worksheet = WorksheetSchema(
            name="Sample_Worksheet",
            clean_name="sample_worksheet",
            datasource_id="test_datasource",
            fields=[
                FieldReference(
                    name="category",
                    original_name="[Category]",
                    tableau_instance="[none:Category:nk]",
                    datatype="string",
                    role="dimension",
                    shelf="columns",
                    derivation="None",
                    display_label="Category",
                ),
                FieldReference(
                    name="sales",
                    original_name="[Sales]",
                    tableau_instance="[sum:Sales:qk]",
                    datatype="number",
                    role="measure",
                    shelf="rows",
                    derivation="Sum",
                    display_label="Sales",
                ),
            ],
            visualization=VisualizationConfig(
                chart_type="bar",
                encodings={"color": "[none:Region:nk]", "size": None, "detail": None},
            ),
            sorting=[],
            filters=[],
        )

        sample_element = DashboardElement(
            element_id="1",
            element_type=ElementType.WORKSHEET,
            position=Position(x=0.0, y=0.0, width=0.5, height=0.5),
            worksheet=sample_worksheet,
        )

        sample_dashboard = DashboardSchema(
            name="Test_Dashboard",
            clean_name="test_dashboard",
            title="Test Dashboard",
            canvas_size={"width": 1000, "height": 800},
            layout_type="newspaper",
            elements=[sample_element],
            global_filters=[],
            cross_filter_enabled=True,
        )

        # Test dashboard generation
        generator = DashboardGenerator()

        migration_data = {
            "dashboards": [sample_dashboard.model_dump()],
            "metadata": {"project_name": "test_project"},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            generated_files = generator.generate(migration_data, temp_dir)

            if generated_files:
                print(f"✅ Generated {len(generated_files)} dashboard files")

                # Read and display the generated content
                with open(generated_files[0], "r") as f:
                    content = f.read()

                print("📝 Generated dashboard content:")
                print("-" * 50)
                print(content)
                print("-" * 50)

                if validate_dashboard_content(content):
                    print("✅ Template rendering test passed")
                    return True
                else:
                    print("❌ Template rendering test failed")
                    return False
            else:
                print("❌ No files generated")
                return False

    except Exception as e:
        print(f"❌ Template rendering test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all dashboard generation tests."""
    print("🚀 Starting Dashboard Generation Tests\n")

    test_results = []

    # Test 1: Template rendering
    test_results.append(("Template Rendering", test_template_rendering()))

    # Test 2: Full pipeline
    test_results.append(("Full Pipeline", test_dashboard_generation()))

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    passed = 0
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    total = len(test_results)
    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Dashboard generation is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
