"""Tests for LookML generator with Book3.twb."""

import tempfile
import shutil
from pathlib import Path
import pytest

from tableau_to_looker_parser.generators.lookml_generator import LookMLGenerator
from tableau_to_looker_parser.core.migration_engine import MigrationEngine


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
def test_lookml_generator_book3():
    """Test: Book3.twb -> JSON -> LookML generator -> LookML files."""
    # Generate JSON from Book3.twb
    book_name = "Book3.twb"
    twb_file = Path(f"sample_twb_files/{book_name}")

    engine = MigrationEngine()
    data = engine.migrate_file(str(twb_file), str(twb_file.parent))

    generator = LookMLGenerator()
    output_dir = Path("sample_twb_files/generated_lookml_book3")
    output_dir.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate LookML files
        generated_files = generator.generate_project_files(data, temp_dir)

        # Validate files generated
        # assert "connection" in generated_files
        assert "views" in generated_files
        assert "model" in generated_files
        # assert len(generated_files["views"]) == len(data["tables"])

        # Validate content
        # with open(generated_files["connection"], "r") as f:
        # assert "connection:" in f.read()

        with open(generated_files["model"], "r") as f:
            model_content = f.read()
            assert "explore:" in model_content
            assert "join:" in model_content  # Book3 has relationships

        # Validate that each view has proper structure
        dimensions_found = False
        measures_found = False

        for view_file in generated_files["views"]:
            with open(view_file, "r") as f:
                content = f.read()
                assert "view:" in content

                # Check for dimensions and measures across all views
                if "dimension:" in content:
                    dimensions_found = True
                if "measure:" in content:
                    measures_found = True

        # At least one view should have measures (v2 parser may classify more fields as measures)
        assert measures_found, "No measures found in any view"

        # For Book3, we expect dimensions in at least one view (movies_data has date dimensions)
        # Note: v2 parser classifies fields more accurately based on metadata aggregation
        assert dimensions_found, "No dimensions found in any view"

        # Copy files for inspection
        # shutil.copy2(generated_files["connection"], output_dir / "connection.lkml")
        shutil.copy2(generated_files["model"], output_dir / "model.lkml")
        for view_file in generated_files["views"]:
            view_name = Path(view_file).stem
            shutil.copy2(view_file, output_dir / f"{view_name}.lkml")

        print("✅ Book3.twb -> LookML generation test passed!")
        print(f"Generated files saved to: {output_dir}")
        print("- connection.lkml")
        print("- model.lkml (with joins)")
        print(f"- {len(generated_files['views'])} view files")
        print(
            f"Used {len(data['dimensions'])} dimensions, {len(data['measures'])} measures, {len(data['relationships'])} relationships"
        )
