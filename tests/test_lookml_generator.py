"""Tests for LookML generator."""

import json
import tempfile
import os
import shutil
from pathlib import Path
import pytest

from tableau_to_looker_parser.generators.lookml_generator import LookMLGenerator
from tableau_to_looker_parser.core.migration_engine import MigrationEngine


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
def test_lookml_generator_real_data():
    """Test: Tableau book -> JSON -> LookML generator -> LookML files."""
    # Generate JSON on the fly from Tableau book
    book_name = "Book3.twb"
    twb_file = Path(f"sample_twb_files/{book_name}")
    
    # Process Tableau file to generate JSON
    engine = MigrationEngine()
    data = engine.migrate_file(str(twb_file), str(twb_file.parent))
    
    # Initialize generator
    generator = LookMLGenerator()
    
    # Create output directory for generated files
    output_dir = Path("sample_twb_files/generated_lookml")
    output_dir.mkdir(exist_ok=True)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate ALL LookML files from JSON data (connection, views, model)
        generated_files = generator.generate_project_files(data, temp_dir)
        
        # Validate all file types were generated
        assert 'connection' in generated_files
        assert 'views' in generated_files
        assert 'model' in generated_files
        
        # Validate files exist
        assert os.path.exists(generated_files['connection'])
        assert len(generated_files['views']) == len(data["tables"])
        assert os.path.exists(generated_files['model'])
        
        # Validate basic content
        with open(generated_files['connection'], 'r') as f:
            assert 'connection:' in f.read()
        
        for view_file in generated_files['views']:
            assert os.path.exists(view_file)
            with open(view_file, 'r') as f:
                content = f.read()
                assert 'view:' in content
                assert 'dimension:' in content
                assert 'measure:' in content
        
        with open(generated_files['model'], 'r') as f:
            model_content = f.read()
            assert 'explore:' in model_content
            assert 'join:' in model_content
        
        # Copy generated files to output directory for inspection
        shutil.copy2(generated_files['connection'], output_dir / "connection.lkml")
        shutil.copy2(generated_files['model'], output_dir / "model.lkml")
        for view_file in generated_files['views']:
            view_name = Path(view_file).stem
            shutil.copy2(view_file, output_dir / f"{view_name}.lkml")
        
        print("✅ Tableau -> JSON -> LookML generation test passed!")
        print(f"Generated files saved to: {output_dir}")
        print(f"- connection.lkml")
        print(f"- model.lkml (with explores and joins)")
        print(f"- {len(generated_files['views'])} view files")
        print(f"Used {len(data['dimensions'])} dimensions, {len(data['measures'])} measures, {len(data['relationships'])} relationships")