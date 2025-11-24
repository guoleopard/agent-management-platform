from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields
from models import db, Agent, AgentLog
import os

app = Flask(__name__)

# 配置API文档
api = Api(app, 
          title='智能体管理平台API', 
          version='1.0', 
          description='智能体管理平台的API接口文档',
          doc='/docs')  # 文档访问路径

# 定义数据模型
agent_model = api.model('Agent', {
    'id': fields.Integer(readonly=True, description='智能体ID'),
    'name': fields.String(required=True, description='智能体名称'),
    'description': fields.String(description='智能体描述'),
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

# 配置数据库
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'db.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)

# 创建数据库表
with app.app_context():
    db.create_all()

# 创建命名空间
ns = api.namespace('agents', description='智能体管理相关操作')

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
            
            # 验证必填字段
            if not data or 'name' not in data:
                return {'error': 'Name is required'}, 400
                
            # 检查智能体是否已存在
            existing_agent = Agent.query.filter_by(name=data['name']).first()
            if existing_agent:
                return {'error': 'Agent already exists'}, 409
                
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
            
            return agent.to_dict(), 201
            
        except Exception as e:
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
            
            # 删除相关日志
            AgentLog.query.filter_by(agent_id=agent.id).delete()
            
            # 删除智能体
            db.session.delete(agent)
            db.session.commit()
            
            return {'message': 'Agent deleted successfully'}, 200
            
        except Exception as e:
            db.session.rollback()
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
