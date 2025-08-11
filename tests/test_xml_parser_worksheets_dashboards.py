#!/usr/bin/env python3
"""
Test script for XML Parser Extensions - Phase 3

Tests the new worksheet and dashboard extraction methods on Bar_charts.twb
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tableau_to_looker_parser.core.xml_parser_v2 import TableauXMLParserV2


def test_xml_parser_phase3():
    """Test the Phase 3 XML parser extensions."""

    print("🔄 Testing XML Parser Phase 3 Extensions")
    print("=" * 50)

    # Initialize parser
    parser = TableauXMLParserV2()

    # Parse Bar_charts.twb
    sample_file = Path("sample_twb_files/Bar_charts.twb")
    if not sample_file.exists():
        print(f"❌ Sample file not found: {sample_file}")
        return

    try:
        print(f"📁 Parsing file: {sample_file}")
        root = parser.parse_file(sample_file)
        print("✅ Successfully parsed XML root")

        # Test worksheet extraction
        print("\n📊 Testing Worksheet Extraction:")
        worksheets = parser.extract_worksheets(root)
        print(f"   Found {len(worksheets)} worksheets")

        if worksheets:
            # Show first few worksheets
            for i, ws in enumerate(worksheets[:3]):
                print(f"   Worksheet {i + 1}: {ws['name']}")
                print(f"     - Clean name: {ws['clean_name']}")
                print(f"     - Datasource: {ws['datasource_id']}")
                print(f"     - Fields: {len(ws['fields'])}")
                print(f"     - Chart type: {ws['visualization']['chart_type']}")

                # Show field details for first worksheet
                if i == 0 and ws["fields"]:
                    print("     - Sample fields:")
                    for j, field in enumerate(ws["fields"][:2]):
                        print(
                            f"       {j + 1}. {field['name']} ({field['role']}) on {field['shelf']}"
                        )

        # Test dashboard extraction
        print("\n🖥️  Testing Dashboard Extraction:")
        dashboards = parser.extract_dashboards(root)
        print(f"   Found {len(dashboards)} dashboards")

        if dashboards:
            # Show first few dashboards
            for i, db in enumerate(dashboards[:2]):
                print(f"   Dashboard {i + 1}: {db['name']}")
                print(f"     - Clean name: {db['clean_name']}")
                print(
                    f"     - Canvas size: {db['canvas_size']['width']}x{db['canvas_size']['height']}"
                )
                print(f"     - Elements: {len(db['elements'])}")
                print(f"     - Layout type: {db['layout_type']}")

                # Show element details
                if db["elements"]:
                    print("     - Sample elements:")
                    for j, element in enumerate(db["elements"][:3]):
                        pos = element["position"]
                        print(
                            f"       {j + 1}. {element['element_type']} at ({pos['x']:.2f}, {pos['y']:.2f})"
                        )
                        if element["element_type"] == "worksheet":
                            print(
                                f"          Worksheet: {element.get('worksheet_name')}"
                            )

        # Save sample output for inspection
        if worksheets and dashboards:
            sample_output = {
                "worksheets": worksheets[:2],  # First 2 worksheets
                "dashboards": dashboards[:1],  # First dashboard
            }

            output_file = Path("xml_parser_phase3_sample_output.json")
            with open(output_file, "w") as f:
                json.dump(sample_output, f, indent=2)
            print(f"\n💾 Sample output saved to: {output_file}")

        print("\n✅ XML Parser Phase 3 Extensions Test PASSED")
        print(f"   - Extracted {len(worksheets)} worksheets")
        print(f"   - Extracted {len(dashboards)} dashboards")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_xml_parser_phase3()
