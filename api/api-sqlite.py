import os
from app import app
from database import db


# Configure SQLAlchemy
basedir = os.path.abspath(os.path.dirname(__file__))
# SQLITE_PATH lets deployments (e.g. Coolify) point the DB at a persistent
# volume. Defaults to the local file for development.
db_path = os.getenv('SQLITE_PATH', os.path.join(basedir, "database.db"))
db_dir = os.path.dirname(db_path)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,  # Verify connections before use
    'pool_recycle': 300,    # Recycle connections every 5 minutes
    'pool_timeout': 20,     # Timeout for getting connection from pool
    'max_overflow': 10      # Maximum overflow connections
}

db.init_app(app)

# Import routes
from routes.schema_routes import *
from routes.bot_routes import *
from routes.core_routes import *

# Create tables and seed initial data on first boot
from utils import seed_default_user, seed_sample_data

with app.app_context():
    db.create_all()
    seed_sample_data()
    seed_default_user()

if __name__ == '__main__':
    print('-'*40, end='')
    print('Server is running', end='')
    print('-'*40)
    app.run(debug=True, use_reloader=True, host='0.0.0.0', port=5000)