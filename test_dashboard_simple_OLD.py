#!/usr/bin/env python3
"""
Simple test to generate and examine dashboard LookML files.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from tableau_to_looker_parser.core.migration_engine import MigrationEngine
from tableau_to_looker_parser.generators.lookml_generator import LookMLGenerator


def test_dashboard_generation():
    """Generate dashboard files and save them to examine."""
    print("Generating dashboard LookML files...")

    # Test file path
    test_file = "sample_twb_files/Bar_charts.twb"
    output_dir = "dashboard_test_output"

    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False

    try:
        # Parse Tableau file
        engine = MigrationEngine(use_v2_parser=True)
        migration_data = engine.migrate_file(test_file, output_dir)

        # Generate LookML files
        generator = LookMLGenerator()
        generated_files = generator.generate_project_files(migration_data, output_dir)

        # Check dashboard files
        dashboard_files = generated_files.get("dashboards", [])
        print(f"✅ Generated {len(dashboard_files)} dashboard files:")

        for file_path in dashboard_files:
            filename = os.path.basename(file_path)
            print(f"   - {filename}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    test_dashboard_generation()
