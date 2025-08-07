#!/usr/bin/env python3
"""
Comprehensive synchronization test for model.lkml, view.lkml, and dashboard.lkml files.

Tests that all references between the files are properly synchronized and would work in Looker.
"""

import sys
import os
import re

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from tableau_to_looker_parser.core.migration_engine import MigrationEngine
from tableau_to_looker_parser.generators.lookml_generator import LookMLGenerator


def test_synchronization():
    """Test complete synchronization between all LookML files."""
    print("🧪 Testing Tableau → Looker Migration Synchronization")
    print("=" * 60)

    # Test file path
    test_file = "sample_twb_files/Bar_charts.twb"
    output_dir = "sync_test_output"

    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False

    try:
        # Step 1: Generate all LookML files
        print("\n1. 📝 Generating LookML files...")
        engine = MigrationEngine(use_v2_parser=True)
        migration_data = engine.migrate_file(test_file, output_dir)

        generator = LookMLGenerator()
        generated_files = generator.generate_project_files(migration_data, output_dir)

        print(f"   ✅ Generated: {list(generated_files.keys())}")

        # Step 2: Load and analyze files
        print("\n2. 🔍 Analyzing file contents...")

        model_file = f"{output_dir}/bigquery_super_store_sales_model.model.lkml"
        view_file = f"{output_dir}/orders.view.lkml"
        dashboard_files = generated_files.get("dashboards", [])

        # Read file contents
        model_content = read_file(model_file)
        view_content = read_file(view_file)

        print(f"   📊 Model file: {len(model_content.splitlines())} lines")
        print(f"   📋 View file: {len(view_content.splitlines())} lines")
        print(f"   🎛️  Dashboard files: {len(dashboard_files)}")

        # Step 3: Extract and validate explores
        print("\n3. 🎯 Validating explore synchronization...")

        model_explores = extract_explores_from_model(model_content)
        dashboard_explores = extract_explores_from_dashboards(dashboard_files)
        view_fields = extract_fields_from_view(view_content)

        print(f"   📈 Model explores: {len(model_explores)}")
        print(f"   📊 Dashboard explores referenced: {len(dashboard_explores)}")
        print(f"   📋 View fields available: {len(view_fields)}")

        # Step 4: Test synchronization
        print("\n4. ✅ Testing synchronization...")

        sync_results = {
            "missing_explores": [],
            "missing_fields": [],
            "orphaned_explores": [],
            "field_mismatches": [],
        }

        # Test 1: Dashboard explores exist in model
        for dashboard_explore in dashboard_explores:
            if dashboard_explore not in model_explores:
                sync_results["missing_explores"].append(dashboard_explore)

        # Test 2: Model explores that aren't used
        for model_explore in model_explores:
            if (
                model_explore not in dashboard_explores and model_explore != "orders"
            ):  # orders is the base table
                sync_results["orphaned_explores"].append(model_explore)

        # Test 3: Dashboard field references exist in view
        dashboard_fields = extract_fields_from_dashboards(dashboard_files)
        for field in dashboard_fields:
            if field not in view_fields:
                sync_results["missing_fields"].append(field)

        # Step 5: Report results
        print("\n5. 📋 Synchronization Results:")

        total_issues = sum(len(v) for v in sync_results.values())

        if total_issues == 0:
            print("   🎉 PERFECT SYNCHRONIZATION!")
            print("   ✅ All dashboard explores exist in model")
            print("   ✅ All dashboard fields exist in view")
            print("   ✅ No orphaned explores found")
            return True
        else:
            print(f"   ⚠️  Found {total_issues} synchronization issues:")

            if sync_results["missing_explores"]:
                print(f"   ❌ Missing explores: {sync_results['missing_explores'][:5]}")

            if sync_results["missing_fields"]:
                print(f"   ❌ Missing fields: {sync_results['missing_fields'][:5]}")

            if sync_results["orphaned_explores"]:
                print(
                    f"   ⚠️  Unused explores: {len(sync_results['orphaned_explores'])}"
                )

            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def read_file(file_path):
    """Read file content safely."""
    try:
        with open(file_path, "r") as f:
            return f.read()
    except Exception as e:
        print(f"   ❌ Could not read {file_path}: {e}")
        return ""


def extract_explores_from_model(model_content):
    """Extract all explore names from model.lkml content."""
    explores = []

    # Find all explore definitions
    explore_pattern = r"explore:\s+(\w+)\s*{"
    matches = re.findall(explore_pattern, model_content)

    for match in matches:
        explores.append(match)

    return explores


def extract_explores_from_dashboards(dashboard_files):
    """Extract all explore references from dashboard files."""
    explores = set()

    for dashboard_file in dashboard_files:
        try:
            content = read_file(dashboard_file)
            # Find explore references in dashboard queries
            explore_pattern = r"explore:\s+(\w+)"
            matches = re.findall(explore_pattern, content)
            explores.update(matches)
        except Exception as e:
            print(f"   ⚠️  Could not process {dashboard_file}: {e}")
            continue

    return list(explores)


def extract_fields_from_view(view_content):
    """Extract all field names from view.lkml content."""
    fields = []

    # Extract dimensions
    dimension_pattern = r"dimension:\s+(\w+)\s*{"
    matches = re.findall(dimension_pattern, view_content)
    fields.extend(matches)

    # Extract measures
    measure_pattern = r"measure:\s+(\w+)\s*{"
    matches = re.findall(measure_pattern, view_content)
    fields.extend(matches)

    return fields


def extract_fields_from_dashboards(dashboard_files):
    """Extract all field references from dashboard files."""
    fields = set()

    for dashboard_file in dashboard_files:
        try:
            content = read_file(dashboard_file)
            # Find field references like explore_name.field_name
            field_pattern = r"(\w+)\.(\w+)"
            matches = re.findall(field_pattern, content)

            for explore_name, field_name in matches:
                # Only include actual field references, not layout properties
                if field_name not in ["column", "row", "width", "height"]:
                    fields.add(field_name)

        except Exception as e:
            print(f"   ⚠️  Could not process {dashboard_file}: {e}")
            continue

    return list(fields)


if __name__ == "__main__":
    success = test_synchronization()
    print(
        f"\n{'🎉 SUCCESS' if success else '❌ FAILED'}: Synchronization test {'passed' if success else 'failed'}"
    )
    sys.exit(0 if success else 1)
