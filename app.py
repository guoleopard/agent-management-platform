from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields
from models import db, Agent, AgentLog
import os

app = Flask(__name__)

# 配置数据库
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'db.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)

# 创建数据库表
with app.app_context():
    db.create_all()

# 初始化Flask-RESTX API
api = Api(
    app,
    version='1.0',
    title='智能体管理平台 API',
    description='轻量级智能体管理平台的RESTful API文档',
    doc='/docs'  # 文档访问路径
)

# 定义命名空间
agent_ns = api.namespace('agents', description='智能体管理相关操作')
log_ns = api.namespace('logs', description='日志管理相关操作')

# 定义数据模型
agent_model = api.model('Agent', {
    'id': fields.Integer(readonly=True, description='智能体ID'),
    'name': fields.String(required=True, description='智能体名称'),
    'description': fields.String(description='智能体描述'),
    'status': fields.String(description='智能体状态', enum=['inactive', 'running', 'paused', 'stopped'], default='inactive'),
    'created_at': fields.DateTime(readonly=True, description='创建时间'),
    'updated_at': fields.DateTime(readonly=True, description='更新时间')
})

log_model = api.model('AgentLog', {
    'id': fields.Integer(readonly=True, description='日志ID'),
    'agent_id': fields.Integer(required=True, description='智能体ID'),
    'agent_name': fields.String(readonly=True, description='智能体名称'),
    'level': fields.String(description='日志级别', enum=['info', 'warning', 'error', 'debug'], default='info'),
    'message': fields.String(required=True, description='日志消息'),
    'timestamp': fields.DateTime(readonly=True, description='日志时间')
})

# 分页响应模型
pagination_model = api.model('Pagination', {
    'total': fields.Integer(description='总记录数'),
    'pages': fields.Integer(description='总页数'),
    'current_page': fields.Integer(description='当前页码'),
    'has_next': fields.Boolean(description='是否有下一页'),
    'has_prev': fields.Boolean(description='是否有上一页')
})

# 智能体列表响应模型
agents_response_model = api.model('AgentsResponse', {
    'agents': fields.List(fields.Nested(agent_model)),
    'pagination': fields.Nested(pagination_model)
})

# 日志列表响应模型
logs_response_model = api.model('LogsResponse', {
    'logs': fields.List(fields.Nested(log_model)),
    'pagination': fields.Nested(pagination_model)
})

# 智能体注册
@agent_ns.route('/')
class AgentList(Resource):
    @agent_ns.expect(agent_model, validate=True)
    @agent_ns.marshal_with(agent_model, code=201)
    @agent_ns.response(400, 'Bad Request')
    @agent_ns.response(409, 'Conflict')
    @agent_ns.response(500, 'Internal Server Error')
    def post(self):
        try:
            data = request.get_json()
            
            # 验证必填字段
            if not data or 'name' not in data:
                api.abort(400, 'Name is required')
                
            # 检查智能体是否已存在
            existing_agent = Agent.query.filter_by(name=data['name']).first()
            if existing_agent:
                api.abort(409, 'Agent already exists')
                
            # 创建新智能体
            agent = Agent(
                name=data['name'],
                description=data.get('description', ''),
                status=data.get('status', 'inactive')
            )
            
            db.session.add(agent)
            db.session.commit()
            
            # 添加注册日志
            log = AgentLog(
                agent_id=agent.id,
                level='info',
                message=f'Agent registered: {agent.name}'
            )
            db.session.add(log)
            db.session.commit()
            
            return agent, 201
            
        except Exception as e:
            db.session.rollback()
            api.abort(500, str(e))

    @agent_ns.marshal_with(agents_response_model)
    @agent_ns.response(500, 'Internal Server Error')
    def get(self):
        try:
            # 分页参数
            page = agent_ns.parser().add_argument('page', type=int, default=1, help='页码').parse_args()['page']
            per_page = agent_ns.parser().add_argument('per_page', type=int, default=10, help='每页记录数').parse_args()['per_page']
            
            # 查询智能体
            agents = Agent.query.paginate(page=page, per_page=per_page, error_out=False)
            
            # 构造响应
            response = {
                'agents': agents.items,
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
            api.abort(500, str(e))

# 获取单个智能体
@agent_ns.route('/<int:agent_id>')
class AgentResource(Resource):
    @agent_ns.marshal_with(agent_model)
    @agent_ns.response(404, 'Not Found')
    @agent_ns.response(500, 'Internal Server Error')
    def get(self, agent_id):
        try:
            agent = Agent.query.get_or_404(agent_id)
            return agent, 200
            
        except Exception as e:
            api.abort(500, str(e))

    @agent_ns.expect(agent_model, validate=True)
    @agent_ns.marshal_with(agent_model)
    @agent_ns.response(404, 'Not Found')
    @agent_ns.response(500, 'Internal Server Error')
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
            return agent, 200
            
        except Exception as e:
            db.session.rollback()
            api.abort(500, str(e))

    @agent_ns.response(200, 'Success')
    @agent_ns.response(404, 'Not Found')
    @agent_ns.response(500, 'Internal Server Error')
    def delete(self, agent_id):
        try:
            agent = Agent.query.get_or_404(agent_id)
            
            # 删除相关日志
            AgentLog.query.filter_by(agent_id=agent.id).delete()
            
            # 删除智能体
            db.session.delete(agent)
            db.session.commit()
            
            return {'message': 'Agent deleted successfully'}, 200
            
        except Exception as e:
            db.session.rollback()
            api.abort(500, str(e))

# 启动智能体
@agent_ns.route('/<int:agent_id>/start')
class AgentStart(Resource):
    @agent_ns.marshal_with(agent_model)
    @agent_ns.response(404, 'Not Found')
    @agent_ns.response(500, 'Internal Server Error')
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
            return agent, 200
            
        except Exception as e:
            db.session.rollback()
            api.abort(500, str(e))

# 暂停智能体
@agent_ns.route('/<int:agent_id>/pause')
class AgentPause(Resource):
    @agent_ns.marshal_with(agent_model)
    @agent_ns.response(404, 'Not Found')
    @agent_ns.response(500, 'Internal Server Error')
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
            return agent, 200
            
        except Exception as e:
            db.session.rollback()
            api.abort(500, str(e))

# 停止智能体
@agent_ns.route('/<int:agent_id>/stop')
class AgentStop(Resource):
    @agent_ns.marshal_with(agent_model)
    @agent_ns.response(404, 'Not Found')
    @agent_ns.response(500, 'Internal Server Error')
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
            return agent, 200
            
        except Exception as e:
            db.session.rollback()
            api.abort(500, str(e))

# 获取智能体日志
@agent_ns.route('/<int:agent_id>/logs')
class AgentLogs(Resource):
    @agent_ns.marshal_with(logs_response_model)
    @agent_ns.response(404, 'Not Found')
    @agent_ns.response(500, 'Internal Server Error')
    def get(self, agent_id):
        try:
            agent = Agent.query.get_or_404(agent_id)
            
            # 分页参数
            page = agent_ns.parser().add_argument('page', type=int, default=1, help='页码').parse_args()['page']
            per_page = agent_ns.parser().add_argument('per_page', type=int, default=20, help='每页记录数').parse_args()['per_page']
            
            # 查询日志
            logs = AgentLog.query.filter_by(agent_id=agent.id).order_by(AgentLog.timestamp.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            # 构造响应
            response = {
                'logs': logs.items,
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
            api.abort(500, str(e))

# 获取所有日志
@log_ns.route('/')
class LogList(Resource):
    @log_ns.marshal_with(logs_response_model)
    @log_ns.response(500, 'Internal Server Error')
    def get(self):
        try:
            # 分页参数
            page = log_ns.parser().add_argument('page', type=int, default=1, help='页码').parse_args()['page']
            per_page = log_ns.parser().add_argument('per_page', type=int, default=20, help='每页记录数').parse_args()['per_page']
            
            # 查询日志
            logs = AgentLog.query.order_by(AgentLog.timestamp.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            # 构造响应
            response = {
                'logs': logs.items,
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
            api.abort(500, str(e))

if __name__ == '__main__':
    app.run(debug=True)
