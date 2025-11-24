from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Model(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    provider = db.Column(db.String(50), nullable=False, default='ollama')  # ollama, openai, etc.
    base_url = db.Column(db.String(200), nullable=False)  # e.g., http://localhost:11434/v1
    api_key = db.Column(db.String(200), nullable=True)  # For OpenAI compatible APIs
    model_name = db.Column(db.String(100), nullable=False)  # e.g., llama3, gpt-3.5-turbo
    max_tokens = db.Column(db.Integer, nullable=False, default=4096)
    temperature = db.Column(db.Float, nullable=False, default=0.7)
    top_p = db.Column(db.Float, nullable=False, default=1.0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Model {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'provider': self.provider,
            'base_url': self.base_url,
            'model_name': self.model_name,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Agent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    model_id = db.Column(db.Integer, db.ForeignKey('model.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='inactive')  # inactive, running, paused, stopped
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    model = db.relationship('Model', backref=db.backref('agents', lazy=True))
    
    def __repr__(self):
        return f'<Agent {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'model_id': self.model_id,
            'model_name': self.model.name,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'), nullable=False)
    user_id = db.Column(db.String(100), nullable=False)  # 可以是用户ID或会话标识
    title = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    agent = db.relationship('Agent', backref=db.backref('conversations', lazy=True))
    
    def __repr__(self):
        return f'<Conversation {self.id} - Agent {self.agent.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'agent_name': self.agent.name,
            'user_id': self.user_id,
            'title': self.title,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # user, assistant, system
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    conversation = db.relationship('Conversation', backref=db.backref('messages', lazy=True))
    
    def __repr__(self):
        return f'<Message {self.id} - {self.role}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat()
        }

class AgentLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'), nullable=False)
    level = db.Column(db.String(20), nullable=False)  # info, warning, error, debug
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    agent = db.relationship('Agent', backref=db.backref('logs', lazy=True))
    
    def __repr__(self):
        return f'<AgentLog {self.agent.name} - {self.level}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'agent_name': self.agent.name,
            'level': self.level,
            'message': self.message,
            'timestamp': self.timestamp.isoformat()
        }
