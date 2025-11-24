# Agent Management Platform

## 项目简介
本项目是一套轻量级的 **智能体管理平台** 示例，旨在帮助 AI 大模型测试人员了解如何构建一个基本的智能体（Agent）管理系统。平台提供以下核心功能：
- **智能体注册**：通过 REST API 注册新的智能体，记录名称、描述、状态等元数据。
- **智能体列表**：展示已注册智能体的概览，支持分页查询。
- **状态管理**：启动、暂停、停止智能体的运行状态。
- **日志查看**：简易的日志接口，帮助调试智能体的行为。

## 适用场景
- 大模型测试环境中，需要统一管理多个对话机器人或任务执行器。
- 教育或培训任务，示例如何使用 Flask（或 FastAPI）+ SQLite 实现基本的 CRUD 操作。

## 技术栈建议
- **后端**：Python + Flask（或 FastAPI）
- **数据库**：SQLite（轻量）
- **依赖管理**：requirements.txt
- **部署**：Docker（可选）

## 结构说明
agent-management-platform
├── app.py               # 主应用入口，定义 API 路由
├── models.py            # 数据模型（SQLAlchemy）
├── db.sqlite3          # 本地 SQLite 数据库文件
├── requirements.txt    # 项目依赖
└── README.md            # 项目说明文档（当前文件）

## 任务要求
请实现上述平台的基本功能，重点关注以下几点：
1. 设计合理的 API 路径与请求/响应结构。  
2. 使用 Flask（或 FastAPI）实现路由逻辑，确保代码可读、易维护。  
3. 使用 SQLite 持久化智能体信息，提供增删改查接口。  
