import os
import re


def update_table_description(table_name: str, new_description: str, schema_file = 'schema.txt') -> bool:
    """
    Updates the description for a given table in the schema.txt file.

    This function reads the schema file, finds the table definition, and
    replaces the old description with the new one by rewriting the file.

    Args:
        table_name: The name of the table to update.
        new_description: The new description text.

    Returns:
        True if the description was updated, False otherwise.
    """
    
    if not os.path.exists(schema_file):
        return False

    try:
        with open(schema_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except IOError:
        return False

    in_target_table = False
    description_line_idx = -1
    table_found = False

    table_pattern = re.compile(r"^\s*Table:\s*" + re.escape(table_name) + r"\b", re.IGNORECASE)
    description_pattern = re.compile(r"^\s*Description:", re.IGNORECASE)

    for i, line in enumerate(lines):
        if table_pattern.match(line):
            in_target_table = True
            table_found = True
        elif in_target_table:
            if description_pattern.match(line):
                description_line_idx = i
                break  # Found the description, stop searching
            elif line.strip() == "":
                # Reached the end of the table block
                in_target_table = False
                break

    if table_found and description_line_idx != -1:
        old_line = lines[description_line_idx]
        indentation_match = re.match(r"(\s*)", old_line)
        indentation = indentation_match.group(1) if indentation_match else ''
        
        # Ensure the new line has a newline character at the end
        new_line = f"{indentation}Description: {new_description.replace('\n',' ').strip()}\n"

        if old_line == new_line:
            return True  # No change needed

        lines[description_line_idx] = new_line

        try:
            with open(schema_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        except IOError:
            return False

    return False

def update_column_description(table_name: str, column_name: str, new_description: str, schema_file = 'schema.txt') -> bool:
    """
    Updates the description for a given column in a table in the schema.txt file.

    Args:
        table_name: The name of the table containing the column.
        column_name: The name of the column to update.
        new_description: The new description text for the column.

    Returns:
        True if the description was updated, False otherwise.
    """
    
    if not os.path.exists(schema_file):
        return False

    try:
        with open(schema_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except IOError:
        return False

    in_target_table = False
    column_line_idx = -1

    table_pattern = re.compile(r"^\s*Table:\s*" + re.escape(table_name) + r"\b", re.IGNORECASE)
    column_pattern = re.compile(r"^\s+" + re.escape(column_name) + r"\s+\(", re.IGNORECASE)
    next_table_pattern = re.compile(r"^\s*Table:", re.IGNORECASE)


    for i, line in enumerate(lines):
        if table_pattern.match(line):
            in_target_table = True
            continue

        if in_target_table:
            if next_table_pattern.match(line) or not line.strip():
                # Stop if we hit the next table definition or an empty line
                break
            
            if column_pattern.match(line):
                column_line_idx = i
                break

    if column_line_idx != -1:
        old_line = lines[column_line_idx]
        
        # Preserve the part of the line before the description
        if ' - ' in old_line:
            column_definition = old_line.split(' - ', 1)[0]
        else:
            column_definition = old_line.rstrip()

        # Construct the new line
        new_line = f"{column_definition} - {new_description.replace('\n',' ').strip()}\n"

        if old_line == new_line:
            return True  # No change needed

        lines[column_line_idx] = new_line

        try:
            with open(schema_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        except IOError:
            return False

    return False

def append_to_file(content, file_path='schema.txt', newline=True):
    """
    Append content to a file.
    
    Args:
        content (str): Content to append
        file_path (str): Path to the file
        newline (bool): Whether to add a newline before the content (default: True)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(file_path, 'a', encoding='utf-8') as file:
            if newline and content and not content.startswith('\n'):
                file.write('\n\n' + content)
            else:
                file.write(content)
        return True
    
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return False
    except PermissionError:
        print(f"Error: Permission denied to write to '{file_path}'.")
        return False
    except Exception as e:
        print(f"Error appending to file: {str(e)}")
        return False


def get_schema(fileName='schema.txt'):
    with open(fileName, 'r', encoding='utf-8') as file:
        schema = file.read()
    return schema

def extract_table_names(schemas):
    """
    Extract table names from a schema string and return them as a comma-separated string.
    
    Args:
        schemas (str): A string containing schema definitions with table names following
                      the format "Table: table_name"
    
    Returns:
        str: Comma-separated list of table names
    """
    table_names = []
    
    # Split the schemas into lines
    lines = schemas.split('\n')
    column_description=[]
    # Look for lines starting with "Table: "
    for idx, line in enumerate(lines):
        line = line.strip()
        if line.lower().startswith('table:'):
            # Extract the table name (everything after "Table: ")
            nextLine=lines[idx+1].strip()
            table_name = line[6:].strip()
            if nextLine.startswith('Description:'):
                if column_description:
                    table_names[-1] =f'{table_names[-1]}. It also have some columns description:  {'., '.join(column_description)}'
                    column_description.clear()
                table_names.append(f'{table_name} - {nextLine[12:].strip()}')
            else:
                table_names.append(f'{table_name} - ')
        else:
            idx=line.find(' - ')
            if idx!=-1:
                comment=line[idx+2:].strip()
                if comment:
                    column_description.append(comment)
    if column_description:
        table_names[-1] =f'{table_names[-1]}. It also have some columns description: {'., '.join(column_description)}'
        column_description.clear()

    
    # Join the table names with commas
    return '\n'.join(table_names)



def filter_schemas_by_table_names(table_names_str, schemas):
    """
    Filter schemas to include only those that match the specified table names.
    
    Args:
        table_names_str (str): Comma-separated list of table names
        schemas (str): A string containing schema definitions
    
    Returns:
        str: Filtered schemas containing only the specified tables
    """
    # Convert comma-separated string to list and strip whitespace
    table_names = [name.strip() for name in table_names_str.split(',')]
    
    if(len(table_names)>20): return ''
    # Split the schemas into individual table definitions
    schema_lines = schemas.split('\n')
    
    filtered_schema = []
    include_current_table = False
    current_table_name = None
    
    for line in schema_lines:
        # Check if line defines a new table
        if line.strip().lower().startswith('table:'):
            # Extract the table name
            current_table_name = line.strip()[6:].strip()
            # Determine if this table should be included
            include_current_table = current_table_name in table_names
            
            # Add a newline before a new table definition (except for the first one)
            if include_current_table and filtered_schema and filtered_schema[-1].strip():
                filtered_schema.append("")
        
        # Include line if it belongs to a table we want to keep
        if include_current_table and line.strip():
            filtered_schema.append(line)
    
    # Join the lines back together
    return '\n'.join(filtered_schema)