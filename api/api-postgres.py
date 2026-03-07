import os
from app import app
from database import db

schema = os.getenv('SCHEMA','public')

# Configure SQLAlchemy
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgresql@localhost:5432/flask_app')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 3600,
    'pool_timeout': 20,
    'max_overflow': 10,
    'connect_args': {
        'options': f'-csearch_path={schema}'
    }      
}

db.init_app(app)

# Import routes
from routes.schema_routes import *
from routes.bot_routes import *
from routes.core_routes import *

# Create tables
with app.app_context():
    from sqlalchemy import text
    db.session.execute(text(f'CREATE SCHEMA IF NOT EXISTS {schema}'))
    db.create_all()

if __name__ == '__main__':
    print('-'*40, end='')
    print('Server is running', end='')
    print('-'*40)
    app.run(debug=True, use_reloader=True, host='0.0.0.0', port=5000)