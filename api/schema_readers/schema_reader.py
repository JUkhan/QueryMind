from sqlalchemy import inspect, text
from typing import Dict
from models import TableDescription, ColumnComment
import os

class SchemaReader:
    table_desc:Dict[str, str]={}
    column_desc:Dict[str,str]={}
    def __init__(self, db_instance):
        self.db = db_instance
    
    def get_all_tables(self):
        """Get all user tables from the database"""
        inspector = inspect(self.db.engine)
        tables = inspector.get_table_names()
        # Filter out metadata tables
        return [table for table in tables if not table.startswith('table_descriptions') 
                and not table.startswith('column_comments')]
    
    def get_table_info(self, table_name: str) -> Dict:
        """Get detailed information about a table"""
        inspector = inspect(self.db.engine)

        # Get columns
        columns = inspector.get_columns(table_name)
        primary_keys = inspector.get_pk_constraint(table_name)['constrained_columns']
        foreign_keys = inspector.get_foreign_keys(table_name)

        # Get unique constraints (not all dialects support this)
        try:
            unique_constraints = inspector.get_unique_constraints(table_name)
        except NotImplementedError:
            unique_constraints = []
        
        # Process columns
        processed_columns = []
        for column in columns:
            column_info = {
                'name': column['name'],
                'type': str(column['type']),
                'constraints': [],
                'comment': self.get_column_comment(table_name, column['name'])
            }
            
            # Add constraints
            if column['name'] in primary_keys:
                column_info['constraints'].append('Primary Key')
            
            if not column['nullable'] and column['name'] not in primary_keys:
                column_info['constraints'].append('Not Null')
            
            # Check unique constraints
            for unique_constraint in unique_constraints:
                if column['name'] in unique_constraint['column_names']:
                    column_info['constraints'].append('Unique')
            
            # Check foreign keys
            for fk in foreign_keys:
                if column['name'] in fk['constrained_columns']:
                    ref_table = fk['referred_table']
                    ref_column = fk['referred_columns'][0]
                    column_info['constraints'].append(f'Foreign Key -> {ref_table}.{ref_column}')
            
            processed_columns.append(column_info)
        
        return {
            'description': self.get_table_description(table_name),
            'columns': processed_columns
        }
    
    def get_table_description(self, table_name: str) -> str:
        """Get table description from metadata"""
        return self.table_desc.get(table_name,f"Represents {table_name.replace('_', ' ')} data in the system.")
        # table_desc = TableDescription.query.filter_by(table_name=table_name).first()
        # if table_desc:
        #     return table_desc.description
        # return f"Represents {table_name.replace('_', ' ')} data in the system."
    
    def get_column_comment(self, table_name: str, column_name: str) -> str:
        """Get column comment from metadata"""
        return self.column_desc.get(table_name+column_name,'')
        # column_comment = ColumnComment.query.filter_by(
        #     table_name=table_name, 
        #     column_name=column_name
        # ).first()
        # if column_comment:
        #     return column_comment.comment
        # return ""
    
    def format_table_info(self, table_name: str, table_info: Dict) -> str:
        """Format table information for output"""
        output = []
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
    
    def load_table_info(self, table_name):
        self.table_desc = {item.table_name:item.description for item in TableDescription.query.filter_by(table_name=table_name).all()}
        self.column_desc = { item.table_name+item.column_name:item.comment for item in ColumnComment.query.filter_by(table_name=table_name).all()}

    def generate_schema_output(self, output_file: str = None) -> str:
        """Generate formatted schema output"""
        tables = self.get_all_tables()
        schema_parts = []
        print('-----------generate_schema_output-----------')
        
        self.table_desc = {item.table_name:item.description for item in TableDescription.query.all()}
        self.column_desc = { item.table_name+item.column_name:item.comment for item in ColumnComment.query.all()}
        schema=os.getenv('SCHEMA','')
        if schema:
            schema_parts.append(f"=== SCHEMA: {schema.upper()} ===\n")
        
        for table_name in tables:
            table_info = self.get_table_info(table_name)
            schema_parts.append(self.format_table_info(table_name, table_info))
        
        schema_output = '\n\n'.join(schema_parts)
        self.table_desc.clear()
        self.column_desc.clear()
        return schema_output
