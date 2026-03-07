import os
from app import app
from database import db


# Configure SQLAlchemy
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] =  f'sqlite:///{os.path.join(basedir, "database.db")}'
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

# Create tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    print('-'*40, end='')
    print('Server is running', end='')
    print('-'*40)
    app.run(debug=True, use_reloader=True, host='0.0.0.0', port=5000)