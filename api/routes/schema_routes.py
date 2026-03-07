from flask import request, jsonify, render_template_string
from schema_readers.schema_reader import SchemaReader
from models import ColumnComment, TableDescription
from database import db
from app import app
from gen_sql.schema import update_table_description, update_column_description, append_to_file
schema_reader = SchemaReader(db)

# API Routes
@app.route('/')
def index():
    """Main page with schema display"""
    return render_template_string(INDEX_TEMPLATE)

@app.route('/api/schema')
def get_schema():
    """Get formatted schema as JSON or text"""
    format_type = request.args.get('format', 'json')
    
    if format_type == 'text':
        schema_output = schema_reader.generate_schema_output()
        return schema_output, 200, {'Content-Type': 'text/plain'}
    
    # JSON format
    tables = schema_reader.get_all_tables()
    schema_data = {}
    
    for table_name in tables:
        schema_data[table_name] = schema_reader.get_table_info(table_name)
    
    return jsonify(schema_data)

@app.route('/api/schema/file')
def export_schema_file():
    """Export schema to file"""
    filename = request.args.get('filename', 'schema.txt')
    schema_output = schema_reader.generate_schema_output(filename)

    if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(schema_output)
                
    return jsonify({
        'message': f'Schema exported to {filename}',
        'content': ''
    })

@app.route('/api/tables')
def get_tables():
    """Get all tables"""
    tables = schema_reader.get_all_tables()
    return jsonify(tables)

@app.route('/api/tables/<table_name>')
def get_table_info(table_name):
    """Get information about a specific table"""
    try:
        schema_reader.load_table_info(table_name)
        table_info = schema_reader.get_table_info(table_name)
        formatted_info = schema_reader.format_table_info(table_name, table_info)
        return jsonify({
            'table_name': table_name,
            'raw_info': table_info,
            'formatted_info': formatted_info
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/descriptions', methods=['GET'])
def get_table_descriptions():
    """Get all table descriptions"""
    descriptions = TableDescription.query.all()
    return jsonify([desc.to_dict() for desc in descriptions])

def get_schema_description(table_name):
        schema_reader.load_table_info(table_name)
        table_info = schema_reader.get_table_info(table_name)
        return schema_reader.format_table_info(table_name, table_info)

@app.route('/api/descriptions', methods=['POST'])
def add_table_description():
    """Add or update table description"""
    data = request.get_json()
    table_name = data.get('table_name')
    description = data.get('description')
    
    if not table_name or not description:
        return jsonify({'error': 'table_name and description are required'}), 400
    
    # Check if table exists
    if table_name not in schema_reader.get_all_tables():
        return jsonify({'error': f'Table {table_name} does not exist'}), 404
    
    # Create or update description
    table_desc = TableDescription.query.filter_by(table_name=table_name).first()
    if table_desc:
        table_desc.description = description
    else:
        table_desc = TableDescription(table_name=table_name, description=description)
        db.session.add(table_desc)
    
    db.session.commit()
    isUpdate = update_table_description(table_name, description)
    if(not isUpdate):
       append_to_file(get_schema_description(table_name))
    return jsonify({'message': f'Description added for table {table_name}'})

@app.route('/api/comments', methods=['GET'])
def get_column_comments():
    """Get all column comments"""
    comments = ColumnComment.query.all()
    return jsonify([comment.to_dict() for comment in comments])

@app.route('/api/comments', methods=['POST'])
def add_column_comment():
    """Add or update column comment"""
    data = request.get_json()
    table_name = data.get('table_name')
    column_name = data.get('column_name')
    comment = data.get('comment')
    
    if not table_name or not column_name or not comment:
        return jsonify({'error': 'table_name, column_name, and comment are required'}), 400
    
    # Create or update comment
    column_comment = ColumnComment.query.filter_by(
        table_name=table_name, 
        column_name=column_name
    ).first()
    
    if column_comment:
        column_comment.comment = comment
    else:
        column_comment = ColumnComment(
            table_name=table_name, 
            column_name=column_name, 
            comment=comment
        )
        db.session.add(column_comment)
    
    db.session.commit()
    isUpdate = update_column_description(table_name, column_name, comment)
    if(not isUpdate):
       append_to_file(get_schema_description(table_name))
    return jsonify({'message': f'Comment added for {table_name}.{column_name}'})


# HTML Template
INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Database Schema Reader</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jqueryui/1.13.2/themes/ui-lightness/jquery-ui.min.css">
    <style>
         body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .schema-output { background: #f5f5f5; padding: 20px; border-radius: 5px; white-space: pre-wrap; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; }
        input, textarea, select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 3px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .tabs { margin-bottom: 20px; }
        .tab { display: inline-block; padding: 10px 20px; background: #f8f9fa; border: 1px solid #ddd; cursor: pointer; }
        .tab.active { background: #007bff; color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .msg{
            padding: 20px;
            background-color: #007bff;
            color: white;
            margin-bottom:5px;
            position:absolute;
            top:65px;
            left:800px;
            z-index:1000;
        }
        .error{
            background-color: #f44336;
        }
        
        /* Custom styles for searchable inputs */
        .searchable-input {
            position: relative;
        }
        
        .ui-autocomplete {
            max-height: 200px;
            overflow-y: auto;
            overflow-x: hidden;
            z-index: 9999 !important;
            background: white;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        .ui-autocomplete .ui-menu-item {
            margin: 0;
            padding: 0;
            border: none;
        }
        
        .ui-autocomplete .ui-menu-item-wrapper {
            padding: 10px 15px;
            border-bottom: 1px solid #eee;
            display: block;
            color: #333;
            text-decoration: none;
            font-size: 14px;
            cursor: pointer;
        }
        
        .ui-autocomplete .ui-menu-item:last-child .ui-menu-item-wrapper {
            border-bottom: none;
        }
        
        .ui-autocomplete .ui-menu-item .ui-menu-item-wrapper:hover,
        .ui-autocomplete .ui-menu-item.ui-state-hover .ui-menu-item-wrapper {
            background-color: #f8f9fa !important;
            color: #333 !important;
        }
        
        .ui-autocomplete .ui-menu-item.ui-state-active .ui-menu-item-wrapper,
        .ui-autocomplete .ui-menu-item.ui-state-focus .ui-menu-item-wrapper {
            background-color: #007bff !important;
            color: white !important;
            border-color: #007bff !important;
        }
        
        .searchable-input input {
            box-sizing: border-box;
        }
        
        /* Override default jQuery UI styles */
        .ui-widget {
            font-family: Arial, sans-serif;
        }
        
        .ui-widget-content {
            background: white;
            border: 1px solid #ccc;
            color: #333;
        }
        
        .ui-menu .ui-menu-item {
            position: relative;
        }

        #helpdesk-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        #helpdesk-table th, #helpdesk-table td {
            border: 1px solid #ddd;
            padding: 12px 15px;
            text-align: left;
        }
        #helpdesk-table th {
            background-color: #007bff;
            color: white;
            text-transform: uppercase;
            font-size: 14px;
        }
        #helpdesk-table tbody tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        #helpdesk-table tbody tr:hover {
            background-color: #e9ecef;
        }
        #helpdesk-table button {
            padding: 8px 12px;
            border-radius: 4px;
            cursor: pointer;
            border: none;
            color: white;
            font-size: 14px;
        }
        .edit-btn {
            background-color: #ffc107;
        }
        .delete-btn {
            background-color: #dc3545;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Database Schema Reader</h1>
        <div id="msg"></div>
        <div class="tabs">
            <div class="tab active" onclick="showTab('schema')">Schema</div>
            <div class="tab" onclick="showTab('descriptions')">Table Descriptions</div>
            <div class="tab" onclick="showTab('comments')">Column Comments</div>
            <div class="tab" onclick="showTab('helpdesk')">Help Desk</div>
        </div>
        
        <div id="schema" class="tab-content active">
            <h2>Database Schema</h2>
            <button id="btn-load-schema" onclick="loadSchema()">Load Schema</button>
            <button id="btn-export" onclick="exportSchema()">Export to File</button>
            <div id="schema-output" class="schema-output"></div>
        </div>
        
        <div id="descriptions" class="tab-content">
            <h2>Manage Table Descriptions</h2>
            <div class="form-group">
                <label>Table Name:</label>
                <div class="searchable-input">
                    <input type="text" id="desc-table-name" placeholder="Search and select table name...">
                </div>
            </div>
            <div class="form-group">
                <label>Description:</label>
                <textarea id="desc-description" placeholder="Enter table description"></textarea>
            </div>
            <button onclick="addDescription()">Add Description</button>
            <div id="descriptions-list"></div>
        </div>
        
        <div id="comments" class="tab-content">
            <h2>Manage Column Comments</h2>
            <div class="form-group">
                <label>Table Name:</label>
                <div class="searchable-input">
                    <input type="text" id="comment-table-name" placeholder="Search and select table name...">
                </div>
            </div>
            <div class="form-group">
                <label>Column Name:</label>
                <div class="searchable-input">
                    <input type="text" id="comment-column-name" placeholder="Search and select column name...">
                </div>
            </div>
            <div class="form-group">
                <label>Comment:</label>
                <textarea id="comment-comment" placeholder="Enter column comment"></textarea>
            </div>
            <button onclick="addComment()">Add Comment</button>
            <div id="comments-list"></div>
        </div>

        <div id="helpdesk" class="tab-content">
            <h2>Help Desk</h2>
            <button onclick="openHelpDeskModal()">Add New Entry</button>
            <table id="helpdesk-table">
                <thead>
                    <tr>
                        <th>Title</th>
                        <th>Query Description</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>

        <div id="helpdesk-modal" title="Help Desk Entry" style="display:none;">
            <form id="helpdesk-form">
                <input type="hidden" id="helpdesk-title-hidden">
                <div class="form-group">
                    <label for="helpdesk-title">Title</label>
                    <input type="text" id="helpdesk-title" name="title" required>
                </div>
                <div class="form-group">
                    <label for="helpdesk-query-description">Query Description</label>
                    <textarea id="helpdesk-query-description" name="query_description" required></textarea>
                </div>
                <div class="form-group">
                    <label for="helpdesk-query">Query</label>
                    <textarea id="helpdesk-query" name="query"></textarea>
                </div>
            </form>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jqueryui/1.13.2/jquery-ui.min.js"></script>
    <script>
        let selectedTable = null;
        let allTableNames = [];
        
        function desTableSelect(val) {
            getTableInfo(val).then(it => {
                document.getElementById('desc-description').value = it.raw_info.description || '';
            });
        }
        
        function commTableSelect(val) {
            getTableInfo(val).then(it => {
                selectedTable = it;
                const columnNames = it.raw_info.columns.map(col => col.name);
                setupAutocomplete('comment-column-name', columnNames, 'Search and select column name...');
            });
        }
        
        function onColumnSelect(val) {
            if (!selectedTable) {
                showMessage('Select a table name first');
                return;
            }
            const col = selectedTable.raw_info.columns.find(it => it.name === val);
            if (col) {
                document.getElementById('comment-comment').value = col.comment || '';
            }
        }
        
        function showMessage(msg, time = 3000) {
            const div = document.getElementById('msg');
            div.innerHTML = `<span class="msg">${msg}</span>`;
            setTimeout(function() {
                div.innerHTML = '';
            }, time);
        }
        
        function errorMessage(msg, time = 3000) {
            const div = document.getElementById('msg');
            div.innerHTML = `<span class="msg error">${msg}</span>`;
            setTimeout(function() {
                div.innerHTML = '';
            }, time);
        }
        
        function showTab(tabName) {
            // Hide all tabs
            const tabs = document.querySelectorAll('.tab');
            const contents = document.querySelectorAll('.tab-content');
            
            tabs.forEach(tab => tab.classList.remove('active'));
            contents.forEach(content => content.classList.remove('active'));
            
            // Show selected tab
            document.querySelector(`[onclick="showTab('${tabName}')"]`).classList.add('active');
            document.getElementById(tabName).classList.add('active');
        }

        function loadSchema() {
            const btn = document.getElementById('btn-load-schema');
            btn.textContent = 'loading...';
            btn.disabled = true;
            document.getElementById('schema-output').textContent = 'Loading...';
            fetch('/api/schema?format=text')
                .then(response => response.text())
                .then(data => {
                    btn.textContent = 'Load Schema';
                    btn.disabled = false;
                    document.getElementById('schema-output').textContent = data;
                });
        }

        function exportSchema() {
            const btn = document.getElementById('btn-export');
            btn.textContent = 'loading...';
            btn.disabled = true;
            fetch('/api/schema/file?filename=schema.txt')
                .then(response => response.json())
                .then(data => {
                    btn.textContent = 'Export to File';
                    btn.disabled = false;
                    showMessage(data.message);
                });
        }

        function addDescription() {
            const tableName = document.getElementById('desc-table-name').value;
            const description = document.getElementById('desc-description').value;
            
            if (!tableName) {
                errorMessage('Please select a table name');
                return;
            }
            
            fetch('/api/descriptions', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({table_name: tableName, description: description})
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) errorMessage(data.error);
                else showMessage(data.message);
                if (!data.error) {
                    document.getElementById('desc-table-name').value = '';
                    document.getElementById('desc-description').value = '';
                }
            });
        }

        function addComment() {
            const tableName = document.getElementById('comment-table-name').value;
            const columnName = document.getElementById('comment-column-name').value;
            const comment = document.getElementById('comment-comment').value;
            
            if (!tableName) {
                errorMessage('Please select a table name');
                return;
            }
            
            if (!columnName) {
                errorMessage('Please select a column name');
                return;
            }
            
            fetch('/api/comments', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    table_name: tableName, 
                    column_name: columnName, 
                    comment: comment
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) errorMessage(data.error);
                else showMessage(data.message);
                if (!data.error) {
                    document.getElementById('comment-table-name').value = '';
                    document.getElementById('comment-column-name').value = '';
                    document.getElementById('comment-comment').value = '';
                }
            });
        }

        function getAllTableNames() {
            return fetch('/api/tables')
                .then(response => response.json());
        }

        function getTableInfo(tableName) {
            return fetch('/api/tables/' + tableName)
                .then(response => response.json());
        }
        
        // Setup autocomplete for a given input element
        function setupAutocomplete(elementId, options, placeholder) {
            const $element = $('#' + elementId);
            
            // Destroy existing autocomplete if it exists
            if ($element.hasClass('ui-autocomplete-input')) {
                $element.autocomplete('destroy');
            }
            
            $element.attr('placeholder', placeholder);
            
            $element.autocomplete({
                source: options,
                minLength: 0,
                delay: 0,
                autoFocus: true,
                select: function(event, ui) {
                    // Handle selection based on the element
                    if (elementId === 'desc-table-name') {
                        desTableSelect(ui.item.value);
                    } else if (elementId === 'comment-table-name') {
                        commTableSelect(ui.item.value);
                    } else if (elementId === 'comment-column-name') {
                        onColumnSelect(ui.item.value);
                    }
                    return true;
                },
                focus: function(event, ui) {
                    // Prevent the input from being updated when navigating with keyboard
                    return false;
                },
                change: function(event, ui) {
                    // Validate that the entered value is in the list
                    const value = $(this).val();
                    if (value && options.indexOf(value) === -1) {
                        $(this).val('');
                        if (elementId === 'comment-column-name') {
                            document.getElementById('comment-comment').value = '';
                        } else if (elementId === 'desc-table-name') {
                            document.getElementById('desc-description').value = '';
                        }
                        showMessage('Please select a valid option from the list');
                    }
                }
            }).on('click', function() {
                // Show all options when clicking on the input
                if ($(this).val() === '') {
                    $(this).autocomplete('search', '');
                }
            });
        }

        // Load schema on page load
        $(document).ready(function() {
            getAllTableNames().then((tableNames) => {
                allTableNames = tableNames;
                
                // Setup autocomplete for table name inputs
                setupAutocomplete('desc-table-name', tableNames, 'Search and select table name...');
                setupAutocomplete('comment-table-name', tableNames, 'Search and select table name...');
                
                // Initialize column name input as empty
                setupAutocomplete('comment-column-name', [], 'Search and select column name...');
            });

            loadHelpDeskData();
        });

        function loadHelpDeskData() {
            fetch('/api/helpdesk')
                .then(response => response.json())
                .then(data => {
                    const tableBody = document.querySelector('#helpdesk-table tbody');
                    tableBody.innerHTML = '';
                    data.data.forEach(entry => {
                        const row = `
                            <tr>
                                <td>${entry.title}</td>
                                <td>${entry.query_description}</td>
                                <td>
                                    <button class="edit-btn" onclick="editHelpDeskEntry('${entry.title}')">Edit</button>
                                    <button class="delete-btn" onclick="deleteHelpDeskEntry('${entry.title}')">Delete</button>
                                </td>
                            </tr>
                        `;
                        tableBody.innerHTML += row;
                    });
                });
        }

        function openHelpDeskModal(title = null) {
            const form = document.getElementById('helpdesk-form');
            form.reset();
            document.getElementById('helpdesk-title-hidden').value = title || '';

            if (title) {
                fetch(`/api/helpdesk/${title}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.entry) {
                            document.getElementById('helpdesk-title').value = data.entry.title;
                            document.getElementById('helpdesk-title').readOnly = true;
                            document.getElementById('helpdesk-query-description').value = data.entry.query_description;
                            document.getElementById('helpdesk-query').value = data.entry.query;
                        }
                    });
            } else {
                document.getElementById('helpdesk-title').readOnly = false;
            }

            $("#helpdesk-modal").dialog({
                modal: true,
                width: 600,
                buttons: {
                    "Save": function() {
                        saveHelpDeskEntry().then(it=>{
                            if(it){
                             $(this).dialog("close");
                            }
                        });     
                    },
                    Cancel: function() {
                        $(this).dialog("close");
                    }
                }
            });
        }

        function saveHelpDeskEntry() {
            const title = document.getElementById('helpdesk-title').value;
            const queryDescription = document.getElementById('helpdesk-query-description').value;
            const query = document.getElementById('helpdesk-query').value;
            const hiddenTitle = document.getElementById('helpdesk-title-hidden').value;
            if(!title){
                errorMessage('Title is required.')
                return Promise.resolve(false);
            }
            if(!queryDescription){
                errorMessage('Query description is required.')
                return Promise.resolve(false);
            }
            const method = hiddenTitle ? 'PUT' : 'POST';
            const url = hiddenTitle ? `/api/helpdesk/${hiddenTitle}` : '/api/helpdesk';

            return fetch(url, {
                method: method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ title: title, query_description: queryDescription, query:query })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    errorMessage(data.error);
                } else {
                    showMessage(data.message);
                    loadHelpDeskData();
                }
                return true;
            });
        }

        function editHelpDeskEntry(title) {
            openHelpDeskModal(title);
        }

        function deleteHelpDeskEntry(title) {
            if (confirm('Are you sure you want to delete this entry?')) {
                fetch(`/api/helpdesk/${title}`, {
                    method: 'DELETE'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        errorMessage(data.error);
                    } else {
                        showMessage(data.message);
                        loadHelpDeskData();
                    }
                });
            }
        }
    </script>
</body>
</html>
'''
