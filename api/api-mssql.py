import os
from app import app
from database import db

schema = os.getenv('SCHEMA','dbo')

# Configure SQLAlchemy for SQL Server
# Format: mssql+pyodbc://username:password@server/database?driver=ODBC+Driver+17+for+SQL+Server
# Or using trusted connection: mssql+pyodbc://server/database?trusted_connection=yes&driver=ODBC+Driver+17+for+SQL+Server

# Try different driver options if one doesn't work:
# - 'SQL Server'
# - 'ODBC Driver 17 for SQL Server'
# - 'ODBC Driver 18 for SQL Server'
# - 'SQL Server Native Client 11.0'

# For local SQL Server with Windows Authentication
# If you have a named instance like SQLEXPRESS, use: localhost\SQLEXPRESS
DATABASE_URL = os.getenv('DATABASE_URL',
    'mssql+pyodbc://sa:pass123!@localhost/master?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes'
)

# For Docker SQL Server - uncomment this line and comment the one above
# DATABASE_URL = os.getenv('DATABASE_URL',
#     'mssql+pyodbc://sa:pass123!@localhost:1433/master?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes'
# )

print('Database URL:', DATABASE_URL)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 3600,
    'pool_timeout': 20,
    'max_overflow': 10,
    'connect_args': {
        # SQL Server specific connection arguments
        # 'timeout': 30,
        # 'autocommit': False,
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
    # Create schema if it doesn't exist (SQL Server syntax)
    db.session.execute(text(f"IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = '{schema}') EXEC('CREATE SCHEMA {schema}')"))
    db.session.commit()
    db.create_all()

if __name__ == '__main__':
    print('-'*40, end='')
    print('Server is running', end='')
    print('-'*40)
    app.run(debug=True, use_reloader=True, host='0.0.0.0', port=5000)
