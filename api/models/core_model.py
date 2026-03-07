from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from database import db

class TableDescription(db.Model):
    __tablename__ = 'table_descriptions_gen_core'
    
    table_name = db.Column(db.String(100), primary_key=True)
    description = db.Column(db.Text, nullable=False)
    
    def to_dict(self):
        return {
            'table_name': self.table_name,
            'description': self.description
        }

class ColumnComment(db.Model):
    __tablename__ = 'column_comments_gen_core'
    
    table_name = db.Column(db.String(100), primary_key=True)
    column_name = db.Column(db.String(100), primary_key=True)
    comment = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'table_name': self.table_name,
            'column_name': self.column_name,
            'comment': self.comment
        }
    

class Dashboard(db.Model):
    __tablename__ = 'dashboard_gen_core'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    type = db.Column(db.Text, nullable=False)
    query = db.Column(db.Text, nullable=False)
    columns = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.String(80), nullable=False)
    json_config = db.Column(db.Text, nullable=True)
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'type': self.type,
            'query':self.query,
            'columns':self.columns,
            'created_at': self.created_at.isoformat(),
            'user_id': self.user_id,
            'json_config': self.json_config
        }

class HelpDesk(db.Model):
    __tablename__ = 'helpdesk_gen_core'
    title = db.Column(db.String(255), primary_key=True)
    query_description = db.Column(db.Text, nullable=False)
    query_text = db.Column('query', db.Text, nullable=True) 
    def to_dict(self):
        return {
            'title': self.title,
            'query_description': self.query_description,
            'query':self.query_text
        }
