#!/usr/bin/env python3
"""
Test Enhanced Chart Type Detection Against Connected Devices Dashboard

This script tests our enhanced chart type detection system using the real
Connected Devices Detail dashboard to validate the patterns we identified.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Import after path modification to avoid E402 linting error
from tableau_to_looker_parser.core.migration_engine import MigrationEngine  # noqa: E402
from tableau_to_looker_parser.converters.enhanced_chart_type_detector import (  # noqa: E402
    EnhancedChartTypeDetector,
)


def test_connected_devices_chart_detection():
    """Test chart type detection against Connected Devices dashboard using MigrationEngine."""

    # Path to Connected Devices dashboard
    dashboard_path = project_root / "connected_devices_dashboard" / "Intraday_Sales.twb"
    output_dir = project_root / "connected_devices_test_output"

    if not dashboard_path.exists():
        print(f"❌ Dashboard file not found: {dashboard_path}")
        return False

    print("🔍 Testing Enhanced Chart Type Detection")
    print("=" * 60)
    print(f"📊 Dashboard: {dashboard_path.name}")
    print()

    try:
        # Use MigrationEngine with v2 parser for proper data structure
        print("📋 Running migration pipeline...")
        engine = MigrationEngine(use_v2_parser=True)
        migration_data = engine.migrate_file(str(dashboard_path), str(output_dir))

        if not migration_data:
            print("❌ Failed to migrate dashboard")
            return False

        print("✅ Migration completed successfully!")

        # Get worksheets from migration data
        worksheets = migration_data.get("worksheets", [])
        dashboards = migration_data.get("dashboards", [])

        print(f"   📄 Worksheets: {len(worksheets)}")
        print(f"   📊 Dashboards: {len(dashboards)}")
        print()

        # Complete Connected Devices Detail Dashboard worksheets
        target_worksheets = [
            # Connected Devices worksheets
            "CD detail",  # Heatmap table
            "CD interval",  # Bar chart
            "CD market ",  # Donut chart
            "CD st",  # Donut chart
            "CD pre",  # Donut chart
            # Connect total (stacked bar from PDF top section)
            "connect total",  # Grouped/stacked bar chart
            # Tablet worksheets (from PDF tablet sections)
            "Tab market",  # Donut chart
            "Tablet st",  # Donut chart
            "tab chan",  # Donut chart
            "tab pre",  # Donut chart
            "Tabular Data",  # Bar chart
        ]

        # Initialize chart detector
        chart_detector = EnhancedChartTypeDetector()
        detection_results = []

        print("🎯 Testing Chart Type Detection:")
        print("-" * 60)

        for worksheet in worksheets:
            worksheet_name = worksheet.get("name", "Unknown")

            # Skip non-target worksheets for focused testing
            if worksheet_name not in target_worksheets:
                continue

            print(f"\n📈 Worksheet: {worksheet_name}")

            # Test chart type detection
            try:
                detection_result = chart_detector.detect_chart_type(worksheet)

                chart_type = detection_result.get("chart_type", "unknown")
                confidence = detection_result.get("confidence", 0.0)
                method = detection_result.get("method", "unknown")
                reasoning = detection_result.get("reasoning", "No reasoning provided")

                print(f"   📊 Chart Type: {chart_type}")
                print(f"   🎯 Confidence: {confidence:.2f}")
                print(f"   🔍 Method: {method}")
                print(f"   💭 Reasoning: {reasoning}")

                # Show additional debug info
                if "pattern_matched" in detection_result:
                    print(f"   🎯 Pattern: {detection_result['pattern_matched']}")
                if "field_analysis" in detection_result:
                    field_analysis = detection_result["field_analysis"]
                    print("   📋 Field Analysis:")
                    for shelf, data in field_analysis.items():
                        if any(data.values()):
                            print(
                                f"      {shelf}: D={len(data['dimensions'])}, M={len(data['measures'])}, Date={len(data['dates'])}"
                            )

                # Debug: Show visualization config
                viz_config = worksheet.get("visualization", {})
                print("   🎨 Visualization Config:")
                print(f"      Chart Type: {viz_config.get('chart_type', 'unknown')}")
                print(f"      Is Dual Axis: {viz_config.get('is_dual_axis', False)}")
                if viz_config.get("color"):
                    print(f"      Color: {viz_config['color']}")
                if viz_config.get("x_axis"):
                    print(
                        f"      X-Axis: {viz_config['x_axis'][:3]}..."
                    )  # Show first 3

                # Debug: Show fields summary
                fields = worksheet.get("fields", [])
                print(f"   📊 Fields Summary: {len(fields)} total")
                field_roles = {}
                field_shelves = {}
                for field in fields:
                    role = field.get("role", "unknown")
                    shelf = field.get("shelf", "unknown")
                    field_roles[role] = field_roles.get(role, 0) + 1
                    field_shelves[shelf] = field_shelves.get(shelf, 0) + 1
                print(f"      Roles: {dict(field_roles)}")
                print(f"      Shelves: {dict(field_shelves)}")

                # Store result for summary
                detection_results.append(
                    {
                        "worksheet": worksheet_name,
                        "chart_type": chart_type,
                        "confidence": confidence,
                        "method": method,
                        "expected_type": get_expected_chart_type(worksheet_name),
                    }
                )

                # Validate against expected results
                expected = get_expected_chart_type(worksheet_name)
                if chart_type == expected:
                    print(f"   ✅ CORRECT: Detected {chart_type} (expected {expected})")
                else:
                    print(
                        f"   ❌ INCORRECT: Detected {chart_type} (expected {expected})"
                    )

            except Exception as e:
                print(f"   ❌ Error processing worksheet: {e}")
                import traceback

                traceback.print_exc()
                detection_results.append(
                    {
                        "worksheet": worksheet_name,
                        "chart_type": "error",
                        "confidence": 0.0,
                        "method": "error",
                        "expected_type": get_expected_chart_type(worksheet_name),
                        "error": str(e),
                    }
                )

        # Summary
        print("\n" + "=" * 60)
        print("📊 DETECTION SUMMARY")
        print("=" * 60)

        correct_detections = 0
        total_detections = len(detection_results)

        for result in detection_results:
            status = (
                "✅ CORRECT"
                if result["chart_type"] == result["expected_type"]
                else "❌ INCORRECT"
            )
            print(f"{status}: {result['worksheet']}")
            print(
                f"   Detected: {result['chart_type']} (confidence: {result.get('confidence', 0):.2f})"
            )
            print(f"   Expected: {result['expected_type']}")

            if result["chart_type"] == result["expected_type"]:
                correct_detections += 1
            print()

        accuracy = (
            (correct_detections / total_detections * 100) if total_detections > 0 else 0
        )
        print(f"🎯 ACCURACY: {correct_detections}/{total_detections} ({accuracy:.1f}%)")

        if accuracy >= 80:
            print("🎉 SUCCESS: Chart type detection is working well!")
            return True
        else:
            print("⚠️  WARNING: Chart type detection needs improvement")
            return False

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()
        return False


def get_expected_chart_type(worksheet_name: str) -> str:
    """Get expected chart type for Complete Connected Devices Detail Dashboard."""
    expected_types = {
        # Connected Devices worksheets
        "CD detail": "heatmap",  # Square mark + color/text encoding (matrix table)
        "CD interval": "bar",  # Bar mark + time series (by interval chart)
        "CD market ": "donut",  # Pie mark + dual measures (connected devices donut)
        "CD st": "donut",  # Pie mark + dual measures (connected devices donut)
        "CD pre": "donut",  # Pie mark + dual measures (connected devices donut)
        # Connect total (stacked bar from PDF top section)
        "connect total": "grouped_bar",  # Grouped/stacked bar (connect total section)
        # Tablet worksheets (from PDF tablet sections)
        "Tab market": "donut",  # Pie mark + dual measures (tablets donut)
        "Tablet st": "donut",  # Pie mark + dual measures (tablets donut)
        "tab chan": "donut",  # Pie mark + dual measures (tablets donut)
        "tab pre": "donut",  # Pie mark + dual measures (tablets donut)
        "Tabular Data": "bar",  # Bar mark (tablets bar chart)
    }
    return expected_types.get(worksheet_name, "unknown")


if __name__ == "__main__":
    print("🚀 Starting Connected Devices Chart Detection Test")
    print()

    success = test_connected_devices_chart_detection()

    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
