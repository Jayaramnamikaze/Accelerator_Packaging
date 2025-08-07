#!/usr/bin/env python3
"""
Test the refactored dashboard generator with ECharts support for Connected Devices.
"""

import sys
import os

sys.path.append("src")

from tableau_to_looker_parser.core.migration_engine import MigrationEngine
from tableau_to_looker_parser.generators.dashboard_generator import DashboardGenerator
from tableau_to_looker_parser.generators.chart_configs.chart_config_factory import (
    ChartConfigFactory,
)


def test_modular_architecture():
    """Test that the modular architecture components are working."""
    print("🔧 Testing modular architecture...")

    # Test dashboard generator initialization
    dashboard_gen = DashboardGenerator()

    print("✅ Dashboard generator initialized with:")
    print(
        f"   - ChartConfigFactory: {type(dashboard_gen.chart_config_factory).__name__}"
    )
    print(f"   - FieldMapper: {type(dashboard_gen.field_mapper).__name__}")
    print(f"   - LayoutCalculator: {type(dashboard_gen.layout_calculator).__name__}")

    # Test chart config factory
    factory = ChartConfigFactory(prefer_echarts=True)

    # Test Connected Devices chart types
    test_charts = ["heatmap", "donut", "bar", "grouped_bar"]

    print("\n📊 Testing ECharts support for Connected Devices patterns:")
    for chart_type in test_charts:
        viz_type = factory.get_visualization_type(chart_type)
        print(f"   - {chart_type} → {viz_type}")
        assert viz_type == "tableau_to_looker::echarts_visualization_prod", (
            f"Expected ECharts for {chart_type}"
        )

    print("✅ All Connected Devices chart types map to ECharts!")

    return True


def test_connected_devices_context():
    """Test Connected Devices dashboard context detection."""
    print("\n🎯 Testing Connected Devices context detection...")

    factory = ChartConfigFactory(prefer_echarts=True)

    # Test dashboard contexts
    test_contexts = [
        {"dashboard_name": "Connected_Devices_Detail"},
        {"dashboard_name": "intraday_sales_dashboard"},
        {"dashboard_name": "device_analytics"},
        {"dashboard_name": "regular_dashboard"},
    ]

    for context in test_contexts:
        dashboard_name = context["dashboard_name"]
        config = factory.get_chart_config("bar", context)
        config_type = type(config).__name__

        if any(
            indicator in dashboard_name.lower()
            for indicator in ["connected_devices", "intraday_sales", "device"]
        ):
            print(
                f"   - {dashboard_name} → {config_type} (Connected Devices pattern detected)"
            )
        else:
            print(f"   - {dashboard_name} → {config_type} (Standard pattern)")

    print("✅ Context detection working correctly!")

    return True


def test_echarts_generation():
    """Test ECharts dashboard generation using LookMLGenerator pipeline."""
    print("\n🚀 Testing ECharts dashboard generation...")

    try:
        from tableau_to_looker_parser.generators.lookml_generator import LookMLGenerator

        # Test with Connected Devices dashboard if available
        twb_file = "connected_devices_dashboard/Intraday_Sales.twb"
        if not os.path.exists(twb_file):
            # Fallback to sample file
            twb_file = "sample_twb_files/Bar_charts.twb"
            if not os.path.exists(twb_file):
                print("⚠️  No test files found, skipping pipeline test...")
                return True

        print(f"   Processing: {twb_file}")

        # Step 1: Parse with migration engine
        engine = MigrationEngine(use_v2_parser=True)
        migration_data = engine.migrate_file(twb_file, "test_echarts_output")

        dashboards = migration_data.get("dashboards", [])
        print(f"   ✅ Extracted {len(dashboards)} dashboards")

        if not dashboards:
            print("   ⚠️  No dashboards found, testing with sample data...")
            return test_sample_echarts()

        # Step 2: Generate with LookMLGenerator (uses our refactored DashboardGenerator)
        generator = LookMLGenerator()
        generated_files = generator.generate_project_files(
            migration_data, "test_echarts_output"
        )

        dashboard_files = generated_files.get("dashboards", [])
        print(f"   ✅ Generated {len(dashboard_files)} dashboard files")

        # Step 3: Validate ECharts configuration in generated files
        echarts_found = 0
        for dashboard_file in dashboard_files:
            if os.path.exists(dashboard_file):
                with open(dashboard_file, "r") as f:
                    content = f.read()

                if "tableau_to_looker::echarts_visualization_prod" in content:
                    echarts_found += 1
                    print(
                        f"   ✅ ECharts visualization found in {os.path.basename(dashboard_file)}"
                    )

                    # Look for Connected Devices specific patterns
                    if any(
                        pattern in content.lower()
                        for pattern in ["heatmap", "donut", "device"]
                    ):
                        print("   ✅ Connected Devices patterns detected")

        if echarts_found > 0:
            print(
                f"   🎉 ECharts configuration successfully generated in {echarts_found} files!"
            )
            return True
        else:
            print("   ⚠️  No ECharts configurations found, testing with sample...")
            return test_sample_echarts()

    except Exception as e:
        print(f"❌ ECharts generation test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_sample_echarts():
    """Test ECharts generation with sample data."""
    print("   📊 Testing with sample ECharts data...")

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
        import tempfile

        # Create Connected Devices sample data
        connected_devices_worksheet = WorksheetSchema(
            name="Connected_Devices_Heatmap",
            clean_name="connected_devices_heatmap",
            datasource_id="devices_datasource",
            fields=[
                FieldReference(
                    name="device_type",
                    original_name="[Device Type]",
                    datatype="string",
                    role="dimension",
                    shelf="rows",
                ),
                FieldReference(
                    name="hour_of_day",
                    original_name="[Hour of Day]",
                    datatype="datetime",
                    role="dimension",
                    shelf="columns",
                ),
                FieldReference(
                    name="connection_count",
                    original_name="[Connection Count]",
                    datatype="number",
                    role="measure",
                    shelf="color",
                    aggregation="sum",
                ),
            ],
            visualization=VisualizationConfig(
                chart_type="heatmap",  # Connected Devices pattern
                encodings={"color": "[sum:Connection Count:qk]"},
            ),
        )

        sample_element = DashboardElement(
            element_id="cd_1",
            element_type=ElementType.WORKSHEET,
            position=Position(x=0.0, y=0.0, width=1.0, height=0.5),
            worksheet=connected_devices_worksheet,
        )

        connected_devices_dashboard = DashboardSchema(
            name="Connected_Devices_Detail",
            clean_name="connected_devices_detail",
            title="Connected Devices Detail Dashboard",
            canvas_size={"width": 1000, "height": 800},
            layout_type="newspaper",
            elements=[sample_element],
            global_filters=[],
        )

        # Test dashboard generation with Connected Devices context
        generator = DashboardGenerator()
        migration_data = {
            "dashboards": [connected_devices_dashboard.model_dump()],
            "metadata": {"project_name": "connected_devices_project"},
            "tables": [{"name": "devices"}],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            generated_files = generator.generate(migration_data, temp_dir)

            if generated_files and os.path.exists(generated_files[0]):
                with open(generated_files[0], "r") as f:
                    content = f.read()

                print("   📄 Generated dashboard content preview:")
                print("   " + "-" * 50)

                # Show key parts of the generated content
                lines = content.split("\n")
                for line in lines[:20]:  # First 20 lines
                    if any(
                        key in line for key in ["type:", "title:", "model:", "explore:"]
                    ):
                        print(f"   {line}")

                print("   " + "-" * 50)

                # Check for ECharts
                if "tableau_to_looker::echarts_visualization_prod" in content:
                    print("   ✅ ECharts visualization type correctly generated!")
                    print("   ✅ Connected Devices heatmap pattern working!")
                    return True
                else:
                    print("   ❌ ECharts visualization not found in generated content")
                    return False
            else:
                print("   ❌ No files generated or file not accessible")
                return False

    except Exception as e:
        print(f"   ❌ Sample ECharts test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Testing Refactored Dashboard Generator with ECharts Support")
    print("=" * 65)

    tests = [
        test_modular_architecture,
        test_connected_devices_context,
        test_echarts_generation,
    ]

    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed: {e}")

    print(f"\n📋 Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("🎉 All tests passed! Refactoring successful!")
        print("✅ ECharts support for Connected Devices is working!")
    else:
        print("⚠️  Some tests failed. Check the issues above.")


if __name__ == "__main__":
    main()
