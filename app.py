from flask import Flask, request, jsonify
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

# 智能体注册
@app.route('/agents', methods=['POST'])
def register_agent():
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data or 'name' not in data:
            return jsonify({'error': 'Name is required'}), 400
            
        # 检查智能体是否已存在
        existing_agent = Agent.query.filter_by(name=data['name']).first()
        if existing_agent:
            return jsonify({'error': 'Agent already exists'}), 409
            
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
        
        return jsonify(agent.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 获取智能体列表
@app.route('/agents', methods=['GET'])
def get_agents():
    try:
        # 分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # 查询智能体
        agents = Agent.query.paginate(page=page, per_page=per_page, error_out=False)
        
        # 构造响应
        response = {
            'agents': [agent.to_dict() for agent in agents.items],
            'total': agents.total,
            'pages': agents.pages,
            'current_page': agents.page,
            'has_next': agents.has_next,
            'has_prev': agents.has_prev
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 获取单个智能体
@app.route('/agents/<int:agent_id>', methods=['GET'])
def get_agent(agent_id):
    try:
        agent = Agent.query.get_or_404(agent_id)
        return jsonify(agent.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 更新智能体
@app.route('/agents/<int:agent_id>', methods=['PUT'])
def update_agent(agent_id):
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
        return jsonify(agent.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 删除智能体
@app.route('/agents/<int:agent_id>', methods=['DELETE'])
def delete_agent(agent_id):
    try:
        agent = Agent.query.get_or_404(agent_id)
        
        # 删除相关日志
        AgentLog.query.filter_by(agent_id=agent.id).delete()
        
        # 删除智能体
        db.session.delete(agent)
        db.session.commit()
        
        return jsonify({'message': 'Agent deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 启动智能体
@app.route('/agents/<int:agent_id>/start', methods=['POST'])
def start_agent(agent_id):
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
        return jsonify(agent.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 暂停智能体
@app.route('/agents/<int:agent_id>/pause', methods=['POST'])
def pause_agent(agent_id):
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
        return jsonify(agent.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 停止智能体
@app.route('/agents/<int:agent_id>/stop', methods=['POST'])
def stop_agent(agent_id):
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
        return jsonify(agent.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 获取智能体日志
@app.route('/agents/<int:agent_id>/logs', methods=['GET'])
def get_agent_logs(agent_id):
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
            'total': logs.total,
            'pages': logs.pages,
            'current_page': logs.page,
            'has_next': logs.has_next,
            'has_prev': logs.has_prev
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 获取所有日志
@app.route('/logs', methods=['GET'])
def get_all_logs():
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
            'total': logs.total,
            'pages': logs.pages,
            'current_page': logs.page,
            'has_next': logs.has_next,
            'has_prev': logs.has_prev
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
