from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields
from models import db, Agent, AgentLog, Model, Conversation, Message
import os
import openai
from openai import OpenAIError
from dotenv import load_dotenv
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True

# 配置API文档
api = Api(app, 
          title='智能体管理平台API', 
          version='1.0', 
          description='智能体管理平台的API接口文档',
          doc='/docs')  # 文档访问路径

# 定义数据模型
pagination_model = api.model('Pagination', {
    'page': fields.Integer(description='当前页码'),
    'per_page': fields.Integer(description='每页数量'),
    'total': fields.Integer(description='总数量'),
    'pages': fields.Integer(description='总页数')
})

model_model = api.model('Model', {
    'id': fields.Integer(readonly=True, description='模型ID'),
    'name': fields.String(required=True, description='模型名称'),
    'description': fields.String(description='模型描述'),
    'provider': fields.String(description='模型提供商', enum=['ollama', 'openai'], default='ollama'),
    'base_url': fields.String(required=True, description='模型API地址'),
    'api_key': fields.String(description='API密钥（OpenAI兼容接口需要）'),
    'model_name': fields.String(required=True, description='模型标识（如：llama3, gpt-3.5-turbo）'),
    'max_tokens': fields.Integer(description='最大token数', default=4096),
    'temperature': fields.Float(description='温度参数', default=0.7),
    'top_p': fields.Float(description='top_p参数', default=1.0),
    'created_at': fields.DateTime(readonly=True, description='创建时间'),
    'updated_at': fields.DateTime(readonly=True, description='更新时间')
})

models_response_model = api.model('ModelsResponse', {
    'models': fields.List(fields.Nested(model_model), description='模型列表'),
    'pagination': fields.Nested(pagination_model, description='分页信息')
})

agent_model = api.model('Agent', {
    'id': fields.Integer(readonly=True, description='智能体ID'),
    'name': fields.String(required=True, description='智能体名称'),
    'description': fields.String(description='智能体描述'),
    'model_id': fields.Integer(required=True, description='关联的模型ID'),
    'status': fields.String(description='智能体状态', enum=['inactive', 'running', 'paused', 'stopped']),
    'created_at': fields.DateTime(readonly=True, description='创建时间'),
    'updated_at': fields.DateTime(readonly=True, description='更新时间')
})

agent_log_model = api.model('AgentLog', {
    'id': fields.Integer(readonly=True, description='日志ID'),
    'agent_id': fields.Integer(description='智能体ID'),
    'level': fields.String(description='日志级别', enum=['info', 'warning', 'error']),
    'message': fields.String(description='日志消息'),
    'timestamp': fields.DateTime(readonly=True, description='日志时间')
})

pagination_model = api.model('Pagination', {
    'total': fields.Integer(description='总记录数'),
    'pages': fields.Integer(description='总页数'),
    'current_page': fields.Integer(description='当前页码'),
    'has_next': fields.Boolean(description='是否有下一页'),
    'has_prev': fields.Boolean(description='是否有上一页')
})

agents_response_model = api.model('AgentsResponse', {
    'agents': fields.List(fields.Nested(agent_model), description='智能体列表'),
    'pagination': fields.Nested(pagination_model, description='分页信息')
})

logs_response_model = api.model('LogsResponse', {
    'logs': fields.List(fields.Nested(agent_log_model), description='日志列表'),
    'pagination': fields.Nested(pagination_model, description='分页信息')
})

# 会话相关模型
conversation_model = api.model('Conversation', {
    'id': fields.Integer(readonly=True, description='会话ID'),
    'agent_id': fields.Integer(required=True, description='智能体ID'),
    'user_id': fields.String(required=True, description='用户ID'),
    'title': fields.String(description='会话标题'),
    'created_at': fields.DateTime(readonly=True, description='创建时间'),
    'updated_at': fields.DateTime(readonly=True, description='更新时间')
})

message_model = api.model('Message', {
    'id': fields.Integer(readonly=True, description='消息ID'),
    'conversation_id': fields.Integer(required=True, description='会话ID'),
    'role': fields.String(required=True, description='角色', enum=['user', 'assistant', 'system']),
    'content': fields.String(required=True, description='消息内容'),
    'timestamp': fields.DateTime(readonly=True, description='发送时间')
})

messages_response_model = api.model('MessagesResponse', {
    'messages': fields.List(fields.Nested(message_model), description='消息列表'),
    'pagination': fields.Nested(pagination_model, description='分页信息')
})

# 聊天请求模型
chat_request_model = api.model('ChatRequest', {
    'user_id': fields.String(required=True, description='用户ID'),
    'message': fields.String(required=True, description='用户消息'),
    'conversation_id': fields.Integer(description='会话ID（可选，不提供则创建新会话）')
})

# 聊天响应模型
chat_response_model = api.model('ChatResponse', {
    'conversation_id': fields.Integer(description='会话ID'),
    'response': fields.String(description='智能体回复'),
    'timestamp': fields.DateTime(readonly=True, description='回复时间')
})

# 会话列表响应模型
conversations_response_model = api.model('ConversationsResponse', {
    'conversations': fields.List(fields.Nested(conversation_model), description='会话列表'),
    'pagination': fields.Nested(pagination_model, description='分页信息')
})

# 配置数据库
# 优先使用环境变量中的MySQL配置，否则使用SQLite
if os.getenv('DATABASE_URL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'db.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)

# 创建数据库表
with app.app_context():
    db.create_all()

# 创建命名空间
ns_models = api.namespace('models', description='模型管理相关操作')
ns = api.namespace('agents', description='智能体管理相关操作')
ns_conversations = api.namespace('conversations', description='会话管理相关操作')

# 模型管理
@ns_models.route('/')
class ModelList(Resource):
    @ns_models.doc('create_model')
    @ns_models.expect(model_model)
    @ns_models.marshal_with(model_model, code=201)
    @ns_models.response(400, '缺少必填字段')
    @ns_models.response(409, '模型已存在')
    @ns_models.response(500, '服务器内部错误')
    def post(self):
        try:
            data = request.get_json()
            
            # 验证必填字段
            if not data or 'name' not in data or 'base_url' not in data or 'model_name' not in data:
                return {'error': 'Name, base_url, and model_name are required'}, 400
                
            # 检查模型是否已存在
            existing_model = Model.query.filter_by(name=data['name']).first()
            if existing_model:
                return {'error': 'Model already exists'}, 409
                
            # 创建新模型
            model = Model(
                name=data['name'],
                description=data.get('description', ''),
                provider=data.get('provider', 'ollama'),
                base_url=data['base_url'],
                api_key=data.get('api_key'),
                model_name=data['model_name'],
                max_tokens=data.get('max_tokens', 4096),
                temperature=data.get('temperature', 0.7),
                top_p=data.get('top_p', 1.0)
            )
            
            db.session.add(model)
            db.session.commit()
            
            return model.to_dict(), 201
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

    @ns_models.doc('get_models')
    @ns_models.marshal_with(models_response_model)
    @ns_models.response(500, '服务器内部错误')
    def get(self):
        try:
            # 分页参数
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            
            # 查询模型
            models = Model.query.paginate(page=page, per_page=per_page, error_out=False)
            
            # 构造响应
            response = {
                'models': [model.to_dict() for model in models.items],
                'pagination': {
                    'total': models.total,
                    'pages': models.pages,
                    'current_page': models.page,
                    'has_next': models.has_next,
                    'has_prev': models.has_prev
                }
            }
            
            return response, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

# 获取单个模型
@ns_models.route('/<int:model_id>')
class ModelResource(Resource):
    @ns_models.doc('get_model')
    @ns_models.marshal_with(model_model)
    @ns_models.response(404, '模型不存在')
    @ns_models.response(500, '服务器内部错误')
    def get(self, model_id):
        try:
            model = Model.query.get_or_404(model_id)
            return model.to_dict(), 200
            
        except Exception as e:
            return {'error': str(e)}, 500

    @ns_models.doc('update_model')
    @ns_models.expect(model_model)
    @ns_models.marshal_with(model_model)
    @ns_models.response(404, '模型不存在')
    @ns_models.response(500, '服务器内部错误')
    def put(self, model_id):
        try:
            model = Model.query.get_or_404(model_id)
            data = request.get_json()
            
            # 更新字段
            if 'name' in data:
                model.name = data['name']
            if 'description' in data:
                model.description = data['description']
            if 'provider' in data:
                model.provider = data['provider']
            if 'base_url' in data:
                model.base_url = data['base_url']
            if 'api_key' in data:
                model.api_key = data['api_key']
            if 'model_name' in data:
                model.model_name = data['model_name']
            if 'max_tokens' in data:
                model.max_tokens = data['max_tokens']
            if 'temperature' in data:
                model.temperature = data['temperature']
            if 'top_p' in data:
                model.top_p = data['top_p']
            
            db.session.commit()
            return model.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

    @ns_models.doc('delete_model')
    @ns_models.response(200, '模型删除成功')
    @ns_models.response(404, '模型不存在')
    @ns_models.response(500, '服务器内部错误')
    def delete(self, model_id):
        try:
            model = Model.query.get_or_404(model_id)
            
            # 检查是否有关联的智能体
            if model.agents:
                return {'error': 'Cannot delete model with associated agents'}, 400
            
            # 删除模型
            db.session.delete(model)
            db.session.commit()
            
            return {'message': 'Model deleted successfully'}, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

# 智能体注册
@ns.route('/')
class AgentList(Resource):
    @ns.doc('register_agent')
    @ns.expect(agent_model)
    @ns.marshal_with(agent_model, code=201)
    @ns.response(400, '缺少必填字段')
    @ns.response(409, '智能体已存在')
    @ns.response(500, '服务器内部错误')
    def post(self):
        try:
            data = request.get_json()
            logger.debug(f"Creating agent with data: {data}")
            
            # 验证必填字段
            if not data or 'name' not in data:
                logger.error("Missing required field: name")
                return {'error': 'Name is required'}, 400
                
            # 检查智能体是否已存在
            existing_agent = Agent.query.filter_by(name=data['name']).first()
            if existing_agent:
                logger.error(f"Agent already exists: {data['name']}")
                return {'error': 'Agent already exists'}, 409
                
            # 检查模型是否存在
            model = Model.query.get(data['model_id'])
            if not model:
                logger.error(f"Model not found with id: {data['model_id']}")
                return {'error': 'Model not found'}, 404
                
            # 创建新智能体
            agent = Agent(
                name=data['name'],
                description=data.get('description', ''),
                model_id=data['model_id'],
                status=data.get('status', 'inactive')
            )
            
            db.session.add(agent)
            db.session.commit()
            logger.debug(f"Agent created successfully: {agent.to_dict()}")
            
            # 添加注册日志
            log = AgentLog(
                agent_id=agent.id,
                level='info',
                message=f'Agent registered: {agent.name}'
            )
            db.session.add(log)
            db.session.commit()
            logger.debug(f"Agent log created successfully: {log.to_dict()}")
            
            return agent.to_dict(), 201
            
        except Exception as e:
            logger.error(f"Error creating agent: {str(e)}")
            db.session.rollback()
            return {'error': str(e)}, 500

    @ns.doc('get_agents')
    @ns.marshal_with(agents_response_model)
    @ns.response(500, '服务器内部错误')
    def get(self):
        try:
            # 分页参数
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            
            # 查询智能体
            agents = Agent.query.paginate(page=page, per_page=per_page, error_out=False)
            
            # 构造响应
            response = {
                'agents': [agent.to_dict() for agent in agents.items],
                'pagination': {
                    'total': agents.total,
                    'pages': agents.pages,
                    'current_page': agents.page,
                    'has_next': agents.has_next,
                    'has_prev': agents.has_prev
                }
            }
            
            return response, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

# 获取单个智能体
@ns.route('/<int:agent_id>')
class AgentResource(Resource):
    @ns.doc('get_agent')
    @ns.marshal_with(agent_model)
    @ns.response(404, '智能体不存在')
    @ns.response(500, '服务器内部错误')
    def get(self, agent_id):
        try:
            agent = Agent.query.get_or_404(agent_id)
            return agent.to_dict(), 200
            
        except Exception as e:
            return {'error': str(e)}, 500

    @ns.doc('update_agent')
    @ns.expect(agent_model)
    @ns.marshal_with(agent_model)
    @ns.response(404, '智能体不存在')
    @ns.response(500, '服务器内部错误')
    def put(self, agent_id):
        try:
            agent = Agent.query.get_or_404(agent_id)
            data = request.get_json()
            
            # 更新字段
            if 'name' in data:
                agent.name = data['name']
            if 'description' in data:
                agent.description = data['description']
            if 'status' in data:
                agent.status = data['status']
                # 添加状态变更日志
                log = AgentLog(
                    agent_id=agent.id,
                    level='info',
                    message=f'Agent status changed to: {agent.status}'
                )
                db.session.add(log)
            
            db.session.commit()
            return agent.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

    @ns.doc('delete_agent')
    @ns.response(200, '智能体删除成功')
    @ns.response(404, '智能体不存在')
    @ns.response(500, '服务器内部错误')
    def delete(self, agent_id):
        try:
            agent = Agent.query.get_or_404(agent_id)
            
            # 删除相关会话和消息
            for conversation in agent.conversations:
                Message.query.filter_by(conversation_id=conversation.id).delete()
                db.session.delete(conversation)
            
            # 删除相关日志
            AgentLog.query.filter_by(agent_id=agent.id).delete()
            
            # 删除智能体
            db.session.delete(agent)
            db.session.commit()
            return {'message': 'Agent deleted successfully'}, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

# 智能体聊天接口
@ns.route('/<int:agent_id>/chat')
class AgentChat(Resource):
    @ns.doc('chat_with_agent')
    @ns.expect(chat_request_model)
    @ns.marshal_with(chat_response_model)
    @ns.response(404, '智能体不存在')
    @ns.response(500, '服务器内部错误')
    def post(self, agent_id):
        try:
            agent = Agent.query.get_or_404(agent_id)
            data = request.get_json()
            
            user_id = data['user_id']
            user_message = data['message']
            conversation_id = data.get('conversation_id')
            
            # 获取模型配置
            model = agent.model
            
            # 创建或获取会话
            if conversation_id:
                conversation = Conversation.query.get(conversation_id)
                if not conversation or conversation.agent_id != agent_id:
                    return {'error': 'Conversation not found or does not belong to this agent'}, 404
            else:
                # 创建新会话
                conversation = Conversation(
                    agent_id=agent_id,
                    user_id=user_id,
                    title=user_message[:50] + '...' if len(user_message) > 50 else user_message
                )
                db.session.add(conversation)
                db.session.commit()
            
            # 保存用户消息
            user_msg = Message(
                conversation_id=conversation.id,
                role='user',
                content=user_message
            )
            db.session.add(user_msg)
            db.session.commit()
            
            # 获取历史消息
            history_messages = Message.query.filter_by(conversation_id=conversation.id)\
                .order_by(Message.timestamp.asc())\
                .limit(20)  # 限制历史消息数量
            
            # 构造请求给模型
            openai.api_base = model.base_url
            openai.api_key = model.api_key or 'ollama'  # Ollama不需要API密钥，用任意字符串即可
            
            messages = []
            for msg in history_messages:
                messages.append({
                    'role': msg.role,
                    'content': msg.content
                })
            
            # 调用模型
            response = openai.ChatCompletion.create(
                model=model.model_name,
                messages=messages,
                max_tokens=model.max_tokens,
                temperature=model.temperature,
                top_p=model.top_p
            )
            
            # 保存助手回复
            assistant_response = response.choices[0]['message']['content']
            assistant_msg = Message(
                conversation_id=conversation.id,
                role='assistant',
                content=assistant_response
            )
            db.session.add(assistant_msg)
            db.session.commit()
            
            # 添加日志
            log = AgentLog(
                agent_id=agent.id,
                level='info',
                message=f'Chat with user {user_id}: {user_message[:50]}...'
            )
            db.session.add(log)
            db.session.commit()
            
            return {
                'conversation_id': conversation.id,
                'response': assistant_response,
                'timestamp': assistant_msg.timestamp.isoformat()
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

# 会话管理
@ns_conversations.route('/')
class ConversationList(Resource):
    @ns_conversations.doc('get_conversations')
    @ns_conversations.marshal_with(conversations_response_model)
    @ns_conversations.response(500, '服务器内部错误')
    def get(self):
        try:
            # 分页参数
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            agent_id = request.args.get('agent_id', type=int)
            user_id = request.args.get('user_id')
            
            # 查询会话
            query = Conversation.query
            if agent_id:
                query = query.filter_by(agent_id=agent_id)
            if user_id:
                query = query.filter_by(user_id=user_id)
            
            conversations = query.order_by(Conversation.updated_at.desc())\
                .paginate(page=page, per_page=per_page, error_out=False)
            
            # 构造响应
            response = {
                'conversations': [conv.to_dict() for conv in conversations.items],
                'pagination': {
                    'total': conversations.total,
                    'pages': conversations.pages,
                    'current_page': conversations.page,
                    'has_next': conversations.has_next,
                    'has_prev': conversations.has_prev
                }
            }
            
            return response, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

# 获取单个会话
@ns_conversations.route('/<int:conversation_id>')
class ConversationResource(Resource):
    @ns_conversations.doc('get_conversation')
    @ns_conversations.marshal_with(conversation_model)
    @ns_conversations.response(404, '会话不存在')
    @ns_conversations.response(500, '服务器内部错误')
    def get(self, conversation_id):
        try:
            conversation = Conversation.query.get_or_404(conversation_id)
            return conversation.to_dict(), 200
            
        except Exception as e:
            return {'error': str(e)}, 500

    @ns_conversations.doc('update_conversation')
    @ns_conversations.expect(conversation_model)
    @ns_conversations.marshal_with(conversation_model)
    @ns_conversations.response(404, '会话不存在')
    @ns_conversations.response(500, '服务器内部错误')
    def put(self, conversation_id):
        try:
            conversation = Conversation.query.get_or_404(conversation_id)
            data = request.get_json()
            
            # 更新字段
            if 'title' in data:
                conversation.title = data['title']
            
            db.session.commit()
            return conversation.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

    @ns_conversations.doc('delete_conversation')
    @ns_conversations.response(200, '会话删除成功')
    @ns_conversations.response(404, '会话不存在')
    @ns_conversations.response(500, '服务器内部错误')
    def delete(self, conversation_id):
        try:
            conversation = Conversation.query.get_or_404(conversation_id)
            
            # 删除相关消息
            Message.query.filter_by(conversation_id=conversation.id).delete()
            
            # 删除会话
            db.session.delete(conversation)
            db.session.commit()
            
            return {'message': 'Conversation deleted successfully'}, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

# 获取会话消息
@ns_conversations.route('/<int:conversation_id>/messages')
class ConversationMessages(Resource):
    @ns_conversations.doc('get_conversation_messages')
    @ns_conversations.marshal_with(messages_response_model)
    @ns_conversations.response(404, '会话不存在')
    @ns_conversations.response(500, '服务器内部错误')
    def get(self, conversation_id):
        try:
            conversation = Conversation.query.get_or_404(conversation_id)
            
            # 分页参数
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            
            # 查询消息
            messages = Message.query.filter_by(conversation_id=conversation.id)\
                .order_by(Message.timestamp.asc())\
                .paginate(page=page, per_page=per_page, error_out=False)
            
            # 构造响应
            response = {
                'messages': [msg.to_dict() for msg in messages.items],
                'pagination': {
                    'total': messages.total,
                    'pages': messages.pages,
                    'current_page': messages.page,
                    'has_next': messages.has_next,
                    'has_prev': messages.has_prev
                }
            }
            
            return response, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

# 启动智能体
@ns.route('/<int:agent_id>/start')
class AgentStart(Resource):
    @ns.doc('start_agent')
    @ns.marshal_with(agent_model)
    @ns.response(404, '智能体不存在')
    @ns.response(500, '服务器内部错误')
    def post(self, agent_id):
        try:
            agent = Agent.query.get_or_404(agent_id)
            agent.status = 'running'
            
            # 添加日志
            log = AgentLog(
                agent_id=agent.id,
                level='info',
                message='Agent started'
            )
            db.session.add(log)
            
            db.session.commit()
            return agent.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

# 暂停智能体
@ns.route('/<int:agent_id>/pause')
class AgentPause(Resource):
    @ns.doc('pause_agent')
    @ns.marshal_with(agent_model)
    @ns.response(404, '智能体不存在')
    @ns.response(500, '服务器内部错误')
    def post(self, agent_id):
        try:
            agent = Agent.query.get_or_404(agent_id)
            agent.status = 'paused'
            
            # 添加日志
            log = AgentLog(
                agent_id=agent.id,
                level='info',
                message='Agent paused'
            )
            db.session.add(log)
            
            db.session.commit()
            return agent.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

# 停止智能体
@ns.route('/<int:agent_id>/stop')
class AgentStop(Resource):
    @ns.doc('stop_agent')
    @ns.marshal_with(agent_model)
    @ns.response(404, '智能体不存在')
    @ns.response(500, '服务器内部错误')
    def post(self, agent_id):
        try:
            agent = Agent.query.get_or_404(agent_id)
            agent.status = 'stopped'
            
            # 添加日志
            log = AgentLog(
                agent_id=agent.id,
                level='info',
                message='Agent stopped'
            )
            db.session.add(log)
            
            db.session.commit()
            return agent.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

# 获取智能体日志
@ns.route('/<int:agent_id>/logs')
class AgentLogs(Resource):
    @ns.doc('get_agent_logs')
    @ns.marshal_with(logs_response_model)
    @ns.response(404, '智能体不存在')
    @ns.response(500, '服务器内部错误')
    def get(self, agent_id):
        try:
            agent = Agent.query.get_or_404(agent_id)
            
            # 分页参数
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            
            # 查询日志
            logs = AgentLog.query.filter_by(agent_id=agent.id).order_by(AgentLog.timestamp.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            # 构造响应
            response = {
                'logs': [log.to_dict() for log in logs.items],
                'pagination': {
                    'total': logs.total,
                    'pages': logs.pages,
                    'current_page': logs.page,
                    'has_next': logs.has_next,
                    'has_prev': logs.has_prev
                }
            }
            
            return response, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

# 创建日志命名空间
logs_ns = api.namespace('logs', description='日志管理相关操作')

# 获取所有日志
@logs_ns.route('/')
class AllLogs(Resource):
    @logs_ns.doc('get_all_logs')
    @logs_ns.marshal_with(logs_response_model)
    @logs_ns.response(500, '服务器内部错误')
    def get(self):
        try:
            # 分页参数
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            
            # 查询日志
            logs = AgentLog.query.order_by(AgentLog.timestamp.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            # 构造响应
            response = {
                'logs': [log.to_dict() for log in logs.items],
                'pagination': {
                    'total': logs.total,
                    'pages': logs.pages,
                    'current_page': logs.page,
                    'has_next': logs.has_next,
                    'has_prev': logs.has_prev
                }
            }
            
            return response, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True)
