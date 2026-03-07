from sqlalchemy import inspect, text
from typing import Dict, List, Optional
from models import TableDescription, ColumnComment
class SchemaReaderPostgres:
    def __init__(self, db_instance, schema_name: str = 'public'):
        self.db = db_instance
        self.schema_name = schema_name
    
    def set_schema(self, schema_name: str):
        """Set the schema to work with"""
        self.schema_name = schema_name
    
    def get_all_schemas(self) -> List[str]:
        """Get all schemas in the database"""
        inspector = inspect(self.db.engine)
        return inspector.get_schema_names()
    
    def get_all_tables(self, schema_name: Optional[str] = None) -> List[str]:
        """Get all user tables from the specified schema"""
        schema = schema_name or self.schema_name
        inspector = inspect(self.db.engine)
        
        # Get tables from specific schema
        tables = inspector.get_table_names(schema=schema)
        
        # Filter out metadata tables
        return [table for table in tables if not table.startswith('table_descriptions') 
                and not table.startswith('column_comments')]
    
    def get_table_info(self, table_name: str, schema_name: Optional[str] = None) -> Dict:
        """Get detailed information about a table in the specified schema"""
        schema = schema_name or self.schema_name
        inspector = inspect(self.db.engine)
        
        # Get columns from specific schema
        columns = inspector.get_columns(table_name, schema=schema)
        primary_keys = inspector.get_pk_constraint(table_name, schema=schema)['constrained_columns']
        foreign_keys = inspector.get_foreign_keys(table_name, schema=schema)
        unique_constraints = inspector.get_unique_constraints(table_name, schema=schema)
        indexes = inspector.get_indexes(table_name, schema=schema)
        
        # Process columns
        processed_columns = []
        for column in columns:
            column_info = {
                'name': column['name'],
                'type': str(column['type']),
                'constraints': [],
                'comment': self.get_column_comment(table_name, column['name'], schema)
            }
            
            # Add constraints
            if column['name'] in primary_keys:
                column_info['constraints'].append('Primary Key')
            
            if not column['nullable'] and column['name'] not in primary_keys:
                column_info['constraints'].append('Not Null')
            
            # Check for default values
            if column.get('default') is not None:
                column_info['constraints'].append(f'Default: {column["default"]}')
            
            # Check unique constraints
            for unique_constraint in unique_constraints:
                if column['name'] in unique_constraint['column_names']:
                    column_info['constraints'].append('Unique')
            
            # Check foreign keys
            for fk in foreign_keys:
                if column['name'] in fk['constrained_columns']:
                    ref_table = fk['referred_table']
                    ref_schema = fk.get('referred_schema', schema)
                    ref_column = fk['referred_columns'][0]
                    column_info['constraints'].append(f'Foreign Key -> {ref_schema}.{ref_table}.{ref_column}')
            
            # Check indexes
            for index in indexes:
                if column['name'] in index['column_names']:
                    column_info['constraints'].append(f'Index: {index["name"]}')
            
            processed_columns.append(column_info)
        
        return {
            'schema': schema,
            'description': self.get_table_description(table_name, schema),
            'columns': processed_columns
        }
    
    def get_table_description(self, table_name: str, schema_name: Optional[str] = None) -> str:
        """Get table description from metadata"""
        schema = schema_name or self.schema_name
        try:
            table_desc =TableDescription.query.filter_by(
                table_name=table_name,
                #schema_name=schema
            ).first()
            if table_desc:
                return table_desc.description
        except Exception as e:
            # If TableDescription model doesn't exist, fall back to default
            print('Error::::',str(e))
            pass
        return f"Represents {table_name.replace('_', ' ')} data in the system."
    
    def get_column_comment(self, table_name: str, column_name: str, schema_name: Optional[str] = None) -> str:
        """Get column comment from metadata"""
        schema = schema_name or self.schema_name
        try:
            column_comment = ColumnComment.query.filter_by(
                table_name=table_name,
                column_name=column_name,
                #schema_name=schema
            ).first()
            if column_comment:
                return column_comment.comment
        except Exception:
            # If ColumnComment model doesn't exist, fall back to empty string
            pass
        return ""
    
    def get_schema_functions(self, schema_name: Optional[str] = None) -> List[Dict]:
        """Get all functions/procedures in the specified schema"""
        schema = schema_name or self.schema_name
        
        query = text("""
            SELECT 
                routine_name,
                routine_type,
                data_type as return_type,
                routine_definition
            FROM information_schema.routines 
            WHERE routine_schema = :schema_name
            ORDER BY routine_name
        """)
        
        try:
            result = self.db.session.execute(query, {'schema_name': schema})
            functions = []
            for row in result:
                functions.append({
                    'name': row.routine_name,
                    'type': row.routine_type,
                    'return_type': row.return_type,
                    'definition': row.routine_definition
                })
            return functions
        except Exception as e:
            print(f"Error fetching functions: {e}")
            return []
    
    def get_schema_views(self, schema_name: Optional[str] = None) -> List[str]:
        """Get all views in the specified schema"""
        schema = schema_name or self.schema_name
        inspector = inspect(self.db.engine)
        
        try:
            return inspector.get_view_names(schema=schema)
        except Exception:
            return []
    
    def format_table_info(self, table_name: str, table_info: Dict) -> str:
        """Format table information for output"""
        output = []
        output.append(f"Schema: {table_info['schema']}")
        output.append(f"Table: {table_name}")
        output.append(f"Description: {table_info['description']}")
        
        for column in table_info['columns']:
            column_line = f"        {column['name']} ({column['type']}"
            
            # Add constraints
            if column['constraints']:
                column_line += f", {', '.join(column['constraints'])}"
            
            column_line += ")"
            
            # Add comment if available
            if column['comment']:
                column_line += f" - {column['comment']}"
            
            output.append(column_line)
        
        return '\n'.join(output)
    
    def generate_schema_output(self, schema_name: Optional[str] = None, output_file: str = None) -> str:
        """Generate formatted schema output for all tables in the schema"""
        schema = schema_name or self.schema_name
        tables = self.get_all_tables(schema)
        schema_parts = []
        
        # Add schema header
        schema_parts.append(f"=== SCHEMA: {schema.upper()} ===\n")
        
        # Add tables information
        for table_name in tables:
            table_info = self.get_table_info(table_name, schema)
            schema_parts.append(self.format_table_info(table_name, table_info))
        
        # Add views information
        views = self.get_schema_views(schema)
        if views:
            schema_parts.append(f"\n=== VIEWS IN {schema.upper()} ===")
            for view in views:
                schema_parts.append(f"View: {view}")
        
        # Add functions information
        functions = self.get_schema_functions(schema)
        if functions:
            schema_parts.append(f"\n=== FUNCTIONS IN {schema.upper()} ===")
            for func in functions:
                schema_parts.append(f"Function: {func['name']} ({func['type']}) -> {func['return_type']}")
        
        schema_output = '\n\n'.join(schema_parts)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(schema_output)
        
        return schema_output
