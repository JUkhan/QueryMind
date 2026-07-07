from flask import request, jsonify
from app import app
from database import db
from models.sample_model import User
from models import Dashboard, HelpDesk

@app.route('/api/login', methods=['POST'])
def login():
    """login user authentication"""
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    user = User.query.filter_by(username=username, email=email).first()

    if user is not None:
        return jsonify(user.to_dict())
    # No matching user — return 401 instead of crashing on a None lookup.
    return jsonify({'error': 'Invalid username or email'}), 401


# dashboard crud
@app.route('/api/dashboard', methods=['POST'])
def create_dashboard():
    try:
        data = request.get_json()

        # Create new user
        new_dashboard = Dashboard(
            title= data['title'],
            type= data['type'],
            query=data['query'],
            columns=data['columns'],
            user_id=data['user_id'],
            json_config=data.get('json_config', None)
        )

        db.session.add(new_dashboard)
        db.session.commit()

        return jsonify({
            'message': 'Dashboard created successfully',
            'dashboard': new_dashboard.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# READ - Get all dashboards
@app.route('/api/dashboards/<user_id>', methods=['GET'])
def get_dashboards(user_id):
    print('user-id:',user_id)
    try:
        dashboards = db.session.query(Dashboard).filter_by(user_id=user_id).order_by(Dashboard.created_at.desc()).all()
        dashboards = [das.to_dict() for das in dashboards]

        return jsonify({'data':dashboards}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# READ - Get a single dashboard by ID
@app.route('/api/dashboard/<int:dashboard_id>', methods=['GET'])
def get_dashboard(dashboard_id):
    try:
        dashboard = Dashboard.query.get(dashboard_id)
        if not dashboard:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'dashboard':dashboard.to_dict()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# UPDATE - Update a dashboard
@app.route('/api/dashboard/<int:dashboard_id>', methods=['PUT'])
def update_dashboard(dashboard_id):
    try:
        dashboard = db.session.query(Dashboard).get(dashboard_id)
        if not dashboard:
            return jsonify({'error': 'Dashboard not found'}), 404
        
        data = request.get_json()
        
        # Update fields if provided

        if 'title' in data:
            dashboard.title=data['title']
        if 'columns' in data:
            dashboard.columns=data['columns']
        if 'query' in data:
            dashboard.query = data['query']
        if 'type' in data:
            dashboard.type = data['type']
        if 'user_id' in data:
            dashboard.user_id = data['user_id']
        if 'grid_x' in data:
            dashboard.grid_x = data['grid_x']
        if 'grid_y' in data:
            dashboard.grid_y = data['grid_y']
        if 'grid_w' in data:
            dashboard.grid_w = data['grid_w']
        if 'grid_h' in data:
            dashboard.grid_h = data['grid_h']
        if 'json_config' in data:
            dashboard.json_config = data['json_config']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Dashboard updated successfully',
            'dashboard': dashboard.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# DELETE - Delete a dashboard
@app.route('/api/dashboard/<int:dashboard_id>', methods=['DELETE'])
def delete_user(dashboard_id):
    try:
        user = db.session.query(Dashboard).get(dashboard_id)
        if not user:
            return jsonify({'error': 'Dashboard not found'}), 404
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': 'Dashboard deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# HelpDesk CRUD
@app.route('/api/helpdesk', methods=['POST'])
def create_helpdesk_entry():
    try:
        data = request.get_json()
        new_entry = HelpDesk(
            title=data['title'],
            query_description=data['query_description'],
            query_text=data['query'] 
        )
        db.session.add(new_entry)
        db.session.commit()
        return jsonify({
            'message': 'HelpDesk entry created successfully',
            'entry': new_entry.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/helpdesk', methods=['GET'])
def get_all_helpdesk_entries():
    try:
        entries = HelpDesk.query.all()
        return jsonify({'data': [entry.to_dict() for entry in entries]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/helpdesk/<string:title>', methods=['GET'])
def get_helpdesk_entry(title):
    try:
        entry = HelpDesk.query.get(title)
        if not entry:
            return jsonify({'error': 'HelpDesk entry not found'}), 404
        return jsonify({'entry': entry.to_dict()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/helpdesk/<string:title>', methods=['PUT'])
def update_helpdesk_entry(title):
    try:
        entry = HelpDesk.query.get(title)
        if not entry:
            return jsonify({'error': 'HelpDesk entry not found'}), 404
        
        data = request.get_json()
        
        if 'query_description' in data:
            entry.query_description = data['query_description']

        if 'query' in data:
            entry.query_text = data['query']
            
        db.session.commit()
        
        return jsonify({
            'message': 'HelpDesk entry updated successfully',
            'entry': entry.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/helpdesk/<string:title>', methods=['DELETE'])
def delete_helpdesk_entry(title):
    try:
        entry = HelpDesk.query.get(title)
        if not entry:
            return jsonify({'error': 'HelpDesk entry not found'}), 404

        db.session.delete(entry)
        db.session.commit()

        return jsonify({'message': 'HelpDesk entry deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# Migration endpoint - Migrate grid layout to json_config
@app.route('/api/dashboards/migrate', methods=['POST'])
def migrate_dashboards_to_json_config():
    """
    Migrate all dashboard components from grid_x/grid_y/grid_w/grid_h columns to json_config
    """
    try:
        import json

        # Get all dashboards
        dashboards = Dashboard.query.all()
        migrated_count = 0
        skipped_count = 0
        error_count = 0

        for dashboard in dashboards:
            try:
                # Parse existing json_config
                existing_config = {}
                if dashboard.json_config:
                    try:
                        if isinstance(dashboard.json_config, str):
                            existing_config = json.loads(dashboard.json_config)
                        else:
                            existing_config = dashboard.json_config
                    except:
                        existing_config = {}

                # Skip if already has grid in json_config
                if 'grid' in existing_config:
                    skipped_count += 1
                    continue

                # Check if has old grid columns
                if hasattr(dashboard, 'grid_x') and dashboard.grid_x is not None:
                    # Migrate to json_config
                    existing_config['grid'] = {
                        'x': dashboard.grid_x,
                        'y': dashboard.grid_y,
                        'w': dashboard.grid_w if dashboard.grid_w is not None else 6,
                        'h': dashboard.grid_h if dashboard.grid_h is not None else 4
                    }
                    existing_config['migratedAt'] = str(dashboard.created_at) if hasattr(dashboard, 'created_at') else None
                    existing_config['version'] = '1.0'

                    dashboard.json_config = json.dumps(existing_config)
                    migrated_count += 1
                else:
                    skipped_count += 1

            except Exception as e:
                print(f"Error migrating dashboard {dashboard.id}: {str(e)}")
                error_count += 1
                continue

        db.session.commit()

        return jsonify({
            'message': 'Migration completed',
            'migrated': migrated_count,
            'skipped': skipped_count,
            'errors': error_count,
            'total': len(dashboards)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


