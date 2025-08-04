#!/usr/bin/env python3
"""
Comprehensive dashboard generation and validation test.

Combines functionality from test_dashboard_generation.py and test_dashboard_simple.py
into a single, thorough test suite with Looker compatibility validation.
"""

import sys
import os
import tempfile

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from tableau_to_looker_parser.core.migration_engine import MigrationEngine
from tableau_to_looker_parser.generators.lookml_generator import LookMLGenerator


def test_dashboard_pipeline():
    """Test complete dashboard generation pipeline with persistent output."""
    print("=== Dashboard Generation Pipeline Test ===\n")

    # Test configuration
    test_file = "sample_twb_files/Bar_charts.twb"
    output_dir = "dashboard_test_output"

    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False

    try:
        # Step 1: Parse Tableau file and extract dashboards
        print("1. Parsing Tableau file and extracting dashboards...")
        engine = MigrationEngine(use_v2_parser=True)
        migration_data = engine.migrate_file(test_file, output_dir)

        # Check extraction results
        dashboards = migration_data.get("dashboards", [])
        worksheets = migration_data.get("worksheets", [])

        print(f"   ✅ Extracted {len(dashboards)} dashboards")
        print(f"   ✅ Extracted {len(worksheets)} worksheets")

        if not dashboards:
            print("   ⚠️  No dashboards found in the file")
            return False

        # Display dashboard summary
        for i, dashboard in enumerate(dashboards):
            print(f"   Dashboard {i + 1}: {dashboard.get('name', 'Unknown')}")
            print(f"     - Elements: {len(dashboard.get('elements', []))}")
            print(f"     - Canvas Size: {dashboard.get('canvas_size', {})}")
            print(f"     - Layout Type: {dashboard.get('layout_type', 'unknown')}")

        print()

        # Step 2: Generate LookML files
        print("2. Generating LookML files...")
        generator = LookMLGenerator()
        generated_files = generator.generate_project_files(migration_data, output_dir)

        print(f"   ✅ Generated file types: {list(generated_files.keys())}")

        # Check dashboard files
        dashboard_files = generated_files.get("dashboards", [])
        if not dashboard_files:
            print("   ❌ No dashboard files generated")
            return False

        print(f"   ✅ Generated {len(dashboard_files)} dashboard files:")
        for file_path in dashboard_files:
            filename = os.path.basename(file_path)
            print(f"      - {filename}")

        print()

        # Step 3: Validate generated files
        print("3. Validating generated LookML files...")

        validation_results = []
        for dashboard_file in dashboard_files:
            filename = os.path.basename(dashboard_file)
            print(f"   📄 Validating: {filename}")

            if not os.path.exists(dashboard_file):
                print(f"      ❌ File not found: {dashboard_file}")
                validation_results.append(False)
                continue

            # Read dashboard content
            with open(dashboard_file, "r") as f:
                dashboard_content = f.read()

            # Run validation checks
            basic_valid = validate_dashboard_content(dashboard_content)
            looker_valid = validate_looker_compatibility(dashboard_content)

            if basic_valid and looker_valid:
                print("      ✅ Valid LookML dashboard format")
                print("      ✅ Looker compatible")
                validation_results.append(True)
            else:
                print(
                    f"      ❌ Validation failed - Basic: {basic_valid}, Looker: {looker_valid}"
                )
                validation_results.append(False)

        # Check view and model files
        view_files = generated_files.get("views", [])
        model_file = generated_files.get("model")

        if view_files:
            print(f"   ✅ Generated {len(view_files)} view files")
        if model_file:
            print(f"   ✅ Generated model file: {os.path.basename(model_file)}")

        print()

        # Summary
        passed_validations = sum(validation_results)
        total_validations = len(validation_results)

        if passed_validations == total_validations:
            print(f"🎉 All {total_validations} dashboard files passed validation!")
            return True
        else:
            print(
                f"❌ {passed_validations}/{total_validations} dashboard files passed validation"
            )
            return False

    except Exception as e:
        print(f"❌ Pipeline test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_template_rendering():
    """Test dashboard template rendering with sample data."""
    print("=== Dashboard Template Rendering Test ===\n")

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

        # Create sample data
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

            if not generated_files:
                print("❌ No files generated")
                return False

            print(f"✅ Generated {len(generated_files)} dashboard files")

            # Read and validate content
            with open(generated_files[0], "r") as f:
                content = f.read()

            print("📝 Generated dashboard content:")
            print("-" * 50)
            print(content)
            print("-" * 50)

            basic_valid = validate_dashboard_content(content)
            looker_valid = validate_looker_compatibility(content)

            if basic_valid and looker_valid:
                print("✅ Template rendering test passed")
                return True
            else:
                print(
                    f"❌ Template rendering test failed - Basic: {basic_valid}, Looker: {looker_valid}"
                )
                return False

    except Exception as e:
        print(f"❌ Template rendering test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def validate_dashboard_content(content: str) -> bool:
    """Validate basic LookML dashboard format."""
    required_elements = [
        "dashboard:",
        "title:",
        "layout:",
        "elements:",
        "row:",
        "col:",
        "width:",
        "height:",
    ]

    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)

    if missing_elements:
        print(f"      ⚠️  Missing elements: {missing_elements}")
        return False

    return True


def validate_looker_compatibility(content: str) -> bool:
    """Validate Looker-specific compatibility issues."""
    issues = []

    # Check for YAML document separator (should not be present)
    if content.strip().startswith("---"):
        issues.append("YAML document separator (---) should be removed")

    # Check for empty column values
    if "col: \n" in content or "col:\n" in content:
        issues.append("Empty col values found")

    # Check for required dashboard fields
    required_dashboard_fields = ["preferred_viewer:", "model:", "explore:"]
    for field in required_dashboard_fields:
        if field not in content:
            issues.append(f"Missing required field: {field}")

    # Check for valid chart types
    valid_chart_types = [
        "looker_column",
        "looker_line",
        "looker_scatter",
        "looker_area",
        "looker_bar",
        "looker_pie",
        "looker_donut",
        "text",
    ]

    lines = content.split("\n")
    for line in lines:
        if "type:" in line and not any(
            chart_type in line for chart_type in valid_chart_types
        ):
            if "type: " in line:  # Make sure it's actually a type definition
                issues.append(f"Invalid chart type in line: {line.strip()}")

    if issues:
        print(f"      ⚠️  Looker compatibility issues: {issues}")
        return False

    return True


def validate_dashboard_structure(dashboard: dict) -> bool:
    """Validate dashboard data structure."""
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


def main():
    """Run comprehensive dashboard tests."""
    print("Comprehensive Dashboard Generation Tests\n")

    test_results = []

    # Test 1: Template rendering
    test_results.append(("Template Rendering", test_template_rendering()))

    # Test 2: Full pipeline with validation
    test_results.append(("Pipeline & Validation", test_dashboard_pipeline()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = 0
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:25}: {status}")
        if result:
            passed += 1

    total = len(test_results)
    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("All tests passed! Dashboard generation is working correctly.")
        print("Generated files available in: dashboard_test_output/")
        return True
    else:
        print("Some tests failed. Check the validation output above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
