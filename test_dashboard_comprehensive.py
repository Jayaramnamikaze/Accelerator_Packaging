"""
Simple script to verify JSON generation from MigrationEngine.

Usage:
    python verify_json_generation.py <path_to_tableau_file.twb>
    
Or run without arguments to see usage instructions.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tableau_to_looker_parser.core.migration_engine import MigrationEngine


def verify_json_generation(tableau_file: str, output_dir: str = "output"):
    """
    Verify JSON generation from a Tableau workbook.
    
    Args:
        tableau_file: Path to .twb or .twbx file
        output_dir: Directory to write output JSON
    """
    print(f"🔍 Verifying JSON generation for: {tableau_file}")
    print("-" * 60)
    
    # Check if file exists
    tableau_path = Path(tableau_file)
    if not tableau_path.exists():
        print(f"❌ Error: File not found: {tableau_file}")
        return False
    
    # Initialize engine
    print("📦 Initializing MigrationEngine...")
    try:
        engine = MigrationEngine(use_v2_parser=True)
        print("✅ MigrationEngine initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing engine: {e}")
        return False
    
    # Run migration
    print(f"\n🚀 Processing workbook...")
    try:
        result = engine.migrate_file(tableau_file, output_dir)
        print("✅ Migration completed successfully")
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Verify output
    output_path = Path(output_dir) / "processed_pipeline_output.json"
    if not output_path.exists():
        print(f"❌ Error: Output file not found: {output_path}")
        return False
    
    # Load and display summary
    print(f"\n📊 JSON Output Summary:")
    print("-" * 60)
    
    with open(output_path, 'r', encoding='utf-8') as f:
        output_data = json.load(f)
    
    # Display statistics
    print(f"📁 Source File: {output_data.get('metadata', {}).get('source_file', 'N/A')}")
    print(f"📂 Output Directory: {output_data.get('metadata', {}).get('output_dir', 'N/A')}")
    print()
    print(f"📈 Statistics:")
    print(f"  • Tables: {len(output_data.get('tables', []))}")
    print(f"  • Relationships: {len(output_data.get('relationships', []))}")
    print(f"  • Connections: {len(output_data.get('connections', []))}")
    print(f"  • Dimensions: {len(output_data.get('dimensions', []))}")
    print(f"  • Measures: {len(output_data.get('measures', []))}")
    print(f"  • Parameters: {len(output_data.get('parameters', []))}")
    print(f"  • Calculated Fields: {len(output_data.get('calculated_fields', []))}")
    print(f"  • Worksheets: {len(output_data.get('worksheets', []))}")
    print(f"  • Dashboards: {len(output_data.get('dashboards', []))}")
    print(f"  • Actions: {len(output_data.get('actions', []))}")
    
   
    print(f"\n✅ JSON file generated successfully at: {output_path}")
    print(f"📏 File size: {output_path.stat().st_size / 1024:.2f} KB")
    
    return True


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        sys.exit(1)
    
    tableau_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    
    success = verify_json_generation(tableau_file, output_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

