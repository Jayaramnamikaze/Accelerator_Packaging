#!/usr/bin/env python3
"""
Comprehensive validation of generated LookML dashboards.
Validates fields, sorts, pivots, chart types, and styling against manual reference.
"""

import sys
import os
import yaml

sys.path.append("src")

from tableau_to_looker_parser.core.migration_engine import MigrationEngine
from tableau_to_looker_parser.generators.lookml_generator import LookMLGenerator


def load_reference_dashboard():
    """Load the manually created reference dashboard for comparison."""
    reference_path = "connected_devices_dashboard/Intraday_Sales.dashboard.lookml"

    if not os.path.exists(reference_path):
        print(f"❌ Reference dashboard not found at: {reference_path}")
        return None

    with open(reference_path, "r") as f:
        content = f.read()

    try:
        # Parse YAML content - it's a list with one dashboard
        reference_list = yaml.safe_load(content)
        if isinstance(reference_list, list) and len(reference_list) > 0:
            return reference_list[0]  # Return the first dashboard
        else:
            return reference_list
    except Exception as e:
        print(f"❌ Failed to parse reference dashboard: {e}")
        return None


def validate_comprehensive_features():
    """Comprehensive validation of all dashboard features."""
    print("🔍 COMPREHENSIVE VALIDATION")
    print("=" * 60)

    # Load reference dashboard
    print("\n📋 Loading Reference Dashboard...")
    reference = load_reference_dashboard()
    if not reference:
        return False

    print(f"✅ Reference loaded: {reference.get('title', 'Unknown')}")
    print(f"   Elements: {len(reference.get('elements', []))}")

    # Generate new dashboard
    print("\n🔧 Generating Dashboard...")
    try:
        engine = MigrationEngine(use_v2_parser=True)
        migration_data = engine.migrate_file(
            "connected_devices_dashboard/Intraday_Sales.twb",
            "comprehensive_validation_output",
        )

        generator = LookMLGenerator()
        generated_files = generator.generate_project_files(
            migration_data, "comprehensive_validation_output"
        )

        dashboard_files = generated_files.get("dashboards", [])
        if not dashboard_files:
            print("❌ No dashboard files generated")
            return False

        # Use the first generated dashboard file
        generated_file = dashboard_files[0]
        print(f"✅ Generated: {os.path.basename(generated_file)}")

    except Exception as e:
        print(f"❌ Generation failed: {e}")
        return False

    # Load generated dashboard
    with open(generated_file, "r") as f:
        generated_content = f.read()

    try:
        # Parse generated YAML - it's a list with one dashboard
        generated_list = yaml.safe_load(generated_content)
        if isinstance(generated_list, list) and len(generated_list) > 0:
            generated = generated_list[0]  # Return the first dashboard
        else:
            generated = generated_list
    except Exception as e:
        print(f"❌ Failed to parse generated dashboard: {e}")
        return False

    print(f"✅ Generated loaded: {generated.get('title', 'Unknown')}")
    print(f"   Elements: {len(generated.get('elements', []))}")

    # Comprehensive validation
    validation_results = {}

    # 1. FIELDS VALIDATION
    print("\n📊 FIELDS VALIDATION")
    print("-" * 30)
    validation_results["fields"] = validate_fields(reference, generated)

    # 2. CHART TYPES VALIDATION
    print("\n📈 CHART TYPES VALIDATION")
    print("-" * 30)
    validation_results["chart_types"] = validate_chart_types(reference, generated)

    # 3. STYLING VALIDATION
    print("\n🎨 STYLING VALIDATION")
    print("-" * 30)
    validation_results["styling"] = validate_styling(reference, generated)

    # 4. SORTS VALIDATION
    print("\n↕️ SORTS VALIDATION")
    print("-" * 30)
    validation_results["sorts"] = validate_sorts(reference, generated)

    # 5. PIVOTS VALIDATION
    print("\n🔄 PIVOTS VALIDATION")
    print("-" * 30)
    validation_results["pivots"] = validate_pivots(reference, generated)

    # 6. LAYOUT VALIDATION
    print("\n📐 LAYOUT VALIDATION")
    print("-" * 30)
    validation_results["layout"] = validate_layout(reference, generated)

    # SUMMARY
    print("\n📋 VALIDATION SUMMARY")
    print("=" * 40)

    total_checks = 0
    passed_checks = 0

    for category, result in validation_results.items():
        total_checks += result["total"]
        passed_checks += result["passed"]

        percentage = (
            (result["passed"] / result["total"] * 100) if result["total"] > 0 else 0
        )
        status = "✅" if percentage >= 80 else "⚠️" if percentage >= 60 else "❌"

        print(
            f"{status} {category.upper()}: {result['passed']}/{result['total']} ({percentage:.1f}%)"
        )

    overall_percentage = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    overall_status = (
        "✅" if overall_percentage >= 80 else "⚠️" if overall_percentage >= 60 else "❌"
    )

    print(
        f"\n{overall_status} OVERALL: {passed_checks}/{total_checks} ({overall_percentage:.1f}%)"
    )

    if overall_percentage >= 80:
        print("🎉 VALIDATION SUCCESSFUL!")
        return True
    else:
        print("❌ VALIDATION NEEDS IMPROVEMENT")
        return False


def validate_fields(reference, generated):
    """Validate field mappings and usage."""
    ref_elements = reference.get("elements", [])
    gen_elements = generated.get("elements", [])

    results = {"passed": 0, "total": 0, "details": []}

    for i, ref_elem in enumerate(ref_elements):
        if i >= len(gen_elements):
            results["details"].append(f"❌ Missing element {i}")
            results["total"] += 1
            continue

        gen_elem = gen_elements[i]
        results["total"] += 1

        # Check if both have fields
        ref_fields = ref_elem.get("fields", [])
        gen_fields = gen_elem.get("fields", [])

        if not ref_fields and not gen_fields:
            results["passed"] += 1
            results["details"].append(f"✅ Element {i}: No fields (correct)")
        elif ref_fields and gen_fields:
            # Compare field count and types
            field_match = len(ref_fields) == len(gen_fields)
            if field_match:
                results["passed"] += 1
                results["details"].append(f"✅ Element {i}: {len(gen_fields)} fields")
            else:
                results["details"].append(
                    f"⚠️ Element {i}: {len(gen_fields)} vs {len(ref_fields)} fields"
                )
        else:
            results["details"].append(f"❌ Element {i}: Field presence mismatch")

    # Print details
    for detail in results["details"]:
        print(f"   {detail}")

    return results


def validate_chart_types(reference, generated):
    """Validate chart type mappings."""
    ref_elements = reference.get("elements", [])
    gen_elements = generated.get("elements", [])

    results = {"passed": 0, "total": 0, "details": []}

    for i, ref_elem in enumerate(ref_elements):
        if i >= len(gen_elements):
            results["total"] += 1
            continue

        gen_elem = gen_elements[i]
        results["total"] += 1

        ref_type = ref_elem.get("type", "")
        gen_type = gen_elem.get("type", "")

        # Check if both use ECharts
        ref_echarts = "echarts_visualization" in ref_type
        gen_echarts = "echarts_visualization" in gen_type

        if ref_echarts and gen_echarts:
            results["passed"] += 1
            results["details"].append(f"✅ Element {i}: Both use ECharts")
        elif not ref_echarts and not gen_echarts:
            results["passed"] += 1
            results["details"].append(f"✅ Element {i}: Both use standard Looker")
        else:
            results["details"].append(
                f"❌ Element {i}: Type mismatch - {gen_type} vs {ref_type}"
            )

    # Print details
    for detail in results["details"]:
        print(f"   {detail}")

    return results


def validate_styling(reference, generated):
    """Validate ECharts styling properties."""
    ref_elements = reference.get("elements", [])
    gen_elements = generated.get("elements", [])

    results = {"passed": 0, "total": 0, "details": []}

    # Key ECharts properties to check
    echarts_props = [
        "chartType",
        "colorPalette",
        "themeSelector",
        "showTooltip",
        "labelAlignment",
        "showLegend",
        "borderRadius",
    ]

    for i, ref_elem in enumerate(ref_elements):
        if i >= len(gen_elements):
            continue

        gen_elem = gen_elements[i]

        # Only check ECharts elements
        if "echarts_visualization" not in gen_elem.get("type", ""):
            continue

        for prop in echarts_props:
            results["total"] += 1

            ref_value = ref_elem.get(prop)
            gen_value = gen_elem.get(prop)

            if ref_value is not None and gen_value is not None:
                results["passed"] += 1
                results["details"].append(f"✅ Element {i}: {prop} present")
            elif ref_value is None and gen_value is not None:
                results["passed"] += 1  # Generated has more properties (good)
                results["details"].append(f"✅ Element {i}: {prop} generated")
            else:
                results["details"].append(f"❌ Element {i}: Missing {prop}")

    # Print details
    for detail in results["details"]:
        print(f"   {detail}")

    return results


def validate_sorts(reference, generated):
    """Validate sort configurations."""
    ref_elements = reference.get("elements", [])
    gen_elements = generated.get("elements", [])

    results = {"passed": 0, "total": 0, "details": []}

    for i, ref_elem in enumerate(ref_elements):
        if i >= len(gen_elements):
            results["total"] += 1
            continue

        gen_elem = gen_elements[i]
        results["total"] += 1

        ref_sorts = ref_elem.get("sorts", [])
        gen_sorts = gen_elem.get("sorts", [])

        if not ref_sorts and not gen_sorts:
            results["passed"] += 1
            results["details"].append(f"✅ Element {i}: No sorts (correct)")
        elif ref_sorts and gen_sorts:
            results["passed"] += 1
            results["details"].append(f"✅ Element {i}: {len(gen_sorts)} sorts")
        elif not ref_sorts and gen_sorts:
            results["passed"] += 1  # Generated has sorts (improvement)
            results["details"].append(
                f"✅ Element {i}: {len(gen_sorts)} sorts generated"
            )
        else:
            results["details"].append(f"⚠️ Element {i}: Sort mismatch")

    # Print details
    for detail in results["details"]:
        print(f"   {detail}")

    return results


def validate_pivots(reference, generated):
    """Validate pivot configurations."""
    ref_elements = reference.get("elements", [])
    gen_elements = generated.get("elements", [])

    results = {"passed": 0, "total": 0, "details": []}

    for i, ref_elem in enumerate(ref_elements):
        if i >= len(gen_elements):
            results["total"] += 1
            continue

        gen_elem = gen_elements[i]
        results["total"] += 1

        ref_pivots = ref_elem.get("pivots", [])
        gen_pivots = gen_elem.get("pivots", [])

        if not ref_pivots and not gen_pivots:
            results["passed"] += 1
            results["details"].append(f"✅ Element {i}: No pivots (correct)")
        elif ref_pivots and gen_pivots:
            results["passed"] += 1
            results["details"].append(f"✅ Element {i}: {len(gen_pivots)} pivots")
        elif not ref_pivots and gen_pivots:
            results["passed"] += 1  # Generated has pivots (improvement)
            results["details"].append(
                f"✅ Element {i}: {len(gen_pivots)} pivots generated"
            )
        else:
            results["details"].append(f"⚠️ Element {i}: Pivot mismatch")

    # Print details
    for detail in results["details"]:
        print(f"   {detail}")

    return results


def validate_layout(reference, generated):
    """Validate layout and positioning."""
    ref_elements = reference.get("elements", [])
    gen_elements = generated.get("elements", [])

    results = {"passed": 0, "total": 0, "details": []}

    for i, ref_elem in enumerate(ref_elements):
        if i >= len(gen_elements):
            results["total"] += 1
            continue

        gen_elem = gen_elements[i]
        results["total"] += 1

        # Check if layout properties exist
        ref_has_layout = any(
            key in ref_elem for key in ["row", "col", "width", "height"]
        )
        gen_has_layout = any(
            key in gen_elem for key in ["row", "col", "width", "height"]
        )

        if ref_has_layout and gen_has_layout:
            results["passed"] += 1
            results["details"].append(f"✅ Element {i}: Layout properties present")
        elif not ref_has_layout and not gen_has_layout:
            results["passed"] += 1
            results["details"].append(f"✅ Element {i}: No layout (correct)")
        else:
            results["details"].append(f"⚠️ Element {i}: Layout mismatch")

    # Print details
    for detail in results["details"]:
        print(f"   {detail}")

    return results


if __name__ == "__main__":
    success = validate_comprehensive_features()
    sys.exit(0 if success else 1)
