"""
LookML generator for converting JSON intermediate format to LookML files.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from .template_engine import TemplateEngine

logger = logging.getLogger(__name__)


class LookMLGenerator:
    """Generator for creating LookML files from JSON intermediate format."""
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize the LookML generator.
        
        Args:
            template_dir: Directory containing template files. If None, uses default.
        """
        self.template_engine = TemplateEngine(template_dir)
        
        # LookML file extension
        self.lookml_extension = ".lkml"
        
        logger.info("LookML generator initialized")
    
    def generate_connection_file(self, connection, output_dir: str) -> str:
        """
        Generate a connection.lkml file.
        
        Args:
            connection: Connection data from JSON format
            output_dir: Directory to write the file to
            
        Returns:
            Path to the generated file
        """
        try:
            # Prepare template context
            context = {
                'connection': connection,
                'connection_name': getattr(connection, 'name') or f"bigquery_{getattr(connection, 'dataset', 'default').lower()}",
                'database_type': getattr(connection, 'type', 'unknown'),
                'host': getattr(connection, 'host', getattr(connection, 'server', None)),
                'port': getattr(connection, 'port', None),
                'database': getattr(connection, 'database', getattr(connection, 'dataset', None)),
                'username': getattr(connection, 'username', getattr(connection, 'service_account', None)),
                'schema': getattr(connection, 'schema', None)
            }
            
            # Render template
            content = self.template_engine.render_template('connection.j2', context)
            
            # Write to file
            output_path = Path(output_dir) / f"connection{self.lookml_extension}"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Generated connection file: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to generate connection file: {str(e)}")
            raise
    
    def generate_view_file(self, view, output_dir: str) -> str:
        """
        Generate a view.lkml file.
        
        Args:
            view: View data from JSON format
            output_dir: Directory to write the file to
            
        Returns:
            Path to the generated file
        """
        try:
            # Prepare template context
            context = {
                'view': view,
                'view_name': self._clean_view_name(view.name),
                'table_name': view.table_name,
                'dimensions': view.dimensions,
                'measures': view.measures,
                'has_dimensions': len(view.dimensions) > 0,
                'has_measures': len(view.measures) > 0
            }
            
            # Render template
            content = self.template_engine.render_template('basic_view.j2', context)
            
            # Write to file
            view_filename = f"{self._clean_view_name(view.name)}{self.lookml_extension}"
            output_path = Path(output_dir) / view_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Generated view file: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to generate view file for {view.name}: {str(e)}")
            raise
    
    def generate_model_file(self, migration_data, output_dir: str) -> str:
        """
        Generate a model.lkml file with explores and joins.
        
        Args:
            migration_data: Complete migration data with relationships
            output_dir: Directory to write the file to
            
        Returns:
            Path to the generated file
        """
        try:
            # Process both logical and physical relationships
            all_relationships = migration_data.get("relationships", [])
            
            # Separate logical and physical relationships
            logical_relationships = [r for r in all_relationships 
                                   if r.get("relationship_type") == "logical"]
            physical_relationships = [r for r in all_relationships 
                                    if r.get("relationship_type") == "physical"]
            
            # Create a single primary explore with all joins
            tables = migration_data.get("tables", [])
            if not tables:
                raise ValueError("No tables found in migration data")
            
            # Use the first table as the primary explore
            primary_table = tables[0]
            explore = {
                "name": primary_table["name"],
                "description": f"Explore for {primary_table['name']} with related tables",
                "joins": []
            }
            
            # Add joins from logical relationships first
            for relationship in logical_relationships:
                join_tables = relationship.get("tables", [])
                if len(join_tables) >= 2:
                    # Find the join table (not the primary table)
                    join_table = None
                    for jt in join_tables:
                        table_name = jt.split('.')[-1].strip('[]').replace('[', '').replace(']', '')
                        if table_name != primary_table["name"]:
                            join_table = table_name
                            break
                    
                    if join_table:
                        # Extract join condition from expressions
                        expressions = relationship.get("expression", {}).get("expressions", [])
                        if len(expressions) >= 2:
                            # Parse expressions: "[id (credits)]" and "[id]"
                            left_expr = expressions[0].replace('[', '').replace(']', '')
                            right_expr = expressions[1].replace('[', '').replace(']', '')
                            
                            # Clean field names
                            left_field = left_expr.replace('(', '').replace(')', '').replace(' ', '_').lower()
                            right_field = right_expr.replace('(', '').replace(')', '').replace(' ', '_').lower()
                            
                            # Handle "id_credits" -> "id"
                            if left_field.endswith('_credits'):
                                left_field = left_field.replace('_credits', '')
                            if right_field.endswith('_credits'):
                                right_field = right_field.replace('_credits', '')
                            
                            # Create proper join condition
                            sql_on = f"${{{primary_table['name']}}}.{right_field} = ${{{join_table}}}.{left_field}"
                            
                            join = {
                                "view_name": join_table,
                                "type": relationship.get("join_type", "left_outer"),
                                "sql_on": sql_on,
                                "relationship": "many_to_one"
                            }
                            explore["joins"].append(join)
            
            # Add joins from physical relationships (self-joins and other physical relationships)
            # Track joins to avoid duplicates
            existing_joins = set()
            
            for relationship in physical_relationships:
                join_tables = relationship.get("tables", [])
                table_aliases = relationship.get("table_aliases", {})
                
                # Handle physical relationships (often self-joins)
                if len(join_tables) >= 1 and table_aliases:
                    expressions = relationship.get("expression", {}).get("expressions", [])
                    if len(expressions) >= 2:
                        # Extract join condition expressions
                        left_expr = expressions[0].replace('[', '').replace(']', '')
                        right_expr = expressions[1].replace('[', '').replace(']', '')
                        
                        # Parse the table.field format
                        left_parts = left_expr.split('.')
                        right_parts = right_expr.split('.')
                        
                        if len(left_parts) >= 2 and len(right_parts) >= 2:
                            left_table = left_parts[0]
                            left_field = left_parts[1]
                            right_table = right_parts[0]
                            right_field = right_parts[1]
                            
                            # Determine which table is the join target (not the primary table)
                            join_table = None
                            if left_table != primary_table["name"] and left_table in table_aliases:
                                join_table = left_table
                                join_field = left_field
                                primary_field = right_field
                            elif right_table != primary_table["name"] and right_table in table_aliases:
                                join_table = right_table
                                join_field = right_field
                                primary_field = left_field
                            
                            if join_table and join_table not in existing_joins:
                                # Create join for the alias table
                                join = {
                                    "view_name": join_table,
                                    "type": relationship.get("join_type", "inner"),
                                    "sql_on": f"${{{primary_table['name']}}}.{primary_field} = ${{{join_table}}}.{join_field}",
                                    "relationship": "one_to_one"
                                }
                                explore["joins"].append(join)
                                existing_joins.add(join_table)
            
            # Only create one primary explore to avoid duplicates
            explores = [explore]
            
            # Get connection name from the second connection (BigQuery)
            connections = migration_data.get('connections', [])
            connection_name = 'default_connection'
            for conn in connections:
                if conn.get('type') == 'bigquery' and conn.get('dataset'):
                    connection_name = f"bigquery_{conn.get('dataset', 'default').lower()}"
                    break
            
            context = {
                'project_name': migration_data.get('metadata', {}).get('project_name', 'tableau_migration'),
                'connection_name': connection_name,
                'views': [{"name": table["name"]} for table in migration_data.get("tables", [])],
                'explores': explores
            }
            
            # Render template
            content = self.template_engine.render_template('model.j2', context)
            
            # Write to file
            output_path = Path(output_dir) / f"model{self.lookml_extension}"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Generated model file: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to generate model file: {str(e)}")
            raise

    def generate_project_files(self, migration_data, output_dir: str) -> Dict[str, str]:
        """
        Generate all LookML files for a migration.
        
        Args:
            migration_data: Complete migration data
            output_dir: Directory to write files to
            
        Returns:
            Dictionary mapping file type to file path
        """
        generated_files = {}
        
        try:
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate connection file
            if migration_data.get("connections"):
                # Find the primary BigQuery connection (skip federated wrapper)
                connection_data = None
                for conn in migration_data["connections"]:
                    if conn.get("type") == "bigquery" and conn.get("name"):
                        connection_data = conn
                        break
                
                # Fallback to first non-federated connection
                if not connection_data:
                    for conn in migration_data["connections"]:
                        if conn.get("type") != "federated":
                            connection_data = conn
                            break
                
                # Final fallback to first connection
                if not connection_data:
                    connection_data = migration_data["connections"][0]
                
                from types import SimpleNamespace
                connection = SimpleNamespace(**connection_data)
                connection_file = self.generate_connection_file(connection, output_dir)
                generated_files['connection'] = connection_file
            
            # Generate view files for all tables
            view_files = []
            for table in migration_data.get("tables", []):
                view_data = {
                    "name": table["name"],
                    "table_name": table["table"],
                    "dimensions": migration_data.get("dimensions", [])[:5],
                    "measures": migration_data.get("measures", [])[:3]
                }
                from types import SimpleNamespace
                view = SimpleNamespace(**view_data)
                view_file = self.generate_view_file(view, output_dir)
                view_files.append(view_file)
            
            generated_files['views'] = view_files
            
            # Generate model file with explores and joins
            model_file = self.generate_model_file(migration_data, output_dir)
            generated_files['model'] = model_file
            
            logger.info(f"Generated {len(generated_files)} file types in {output_dir}")
            return generated_files
            
        except Exception as e:
            logger.error(f"Failed to generate project files: {str(e)}")
            raise
    
    def _generate_manifest_file(self, migration_data, output_dir: str) -> str:
        """Generate a basic manifest.lkml file."""
        try:
            context = {
                'project_name': migration_data.metadata.get('project_name', 'tableau_migration'),
                'views': migration_data.views,
                'connections': migration_data.connections
            }
            
            # Use string template for now since we don't have manifest.j2 yet
            manifest_content = f"""# Generated LookML project manifest
# Project: {context['project_name']}

connection: "{context['connections'][0].name if context['connections'] else 'default'}"

# Views
{chr(10).join([f'include: "{self._clean_view_name(view.name)}.lkml"' for view in context['views']])}

# Explores (to be added in Phase 2)
"""
            
            output_path = Path(output_dir) / f"manifest{self.lookml_extension}"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(manifest_content)
            
            logger.info(f"Generated manifest file: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to generate manifest file: {str(e)}")
            raise
    
    def _clean_connection_name(self, name: str) -> str:
        """Clean connection name for LookML."""
        return self.template_engine._clean_name_filter(name)
    
    def _clean_view_name(self, name: str) -> str:
        """Clean view name for LookML."""
        return self.template_engine._clean_name_filter(name)
    
    def validate_output_directory(self, output_dir: str) -> bool:
        """
        Validate that output directory is writable.
        
        Args:
            output_dir: Directory path to validate
            
        Returns:
            True if directory is valid and writable
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Test write access
            test_file = output_path / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            
            return True
            
        except Exception as e:
            logger.error(f"Output directory validation failed: {str(e)}")
            return False