# 文本模型调用服务 (text-service)

## 项目概述

文本模型调用服务是SciTiger AI模型调用微服务体系的一部分，负责处理文本生成、摘要、分析等任务。本服务使用FastAPI框架实现，支持多种文本处理模型的调用，包括DeepSeek、Qwen、智谱AI、Kimi等。

## 功能特性

- **统一认证**：集成SciTigerCore认证系统（可关闭）
- **异步处理**：支持长时间运行的任务
- **多模型支持**：可配置调用不同的AI模型提供商
- **任务管理**：提供任务创建、查询和结果获取的统一接口

## 技术栈

- **FastAPI**：Web框架
- **Pydantic V2**：数据验证和序列化
- **Celery**：异步任务处理
- **Redis**：消息队列
- **MongoDB**：数据存储

## 快速开始

### 环境准备

1. 安装 Python 3.10+ 和依赖工具
2. 安装并启动 MongoDB 和 Redis 服务
3. 克隆项目代码
4. 复制环境变量示例文件

```bash
cp .env.example .env
```

5. 根据需要修改环境变量

### 启动服务

#### 1. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

#### 3. 启动API服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001  --reload
```

#### 4. 启动Celery工作进程

```bash
celery -A app.core.celery_app worker --loglevel=info
```

#### 5. 启动Flower监控（可选）

```bash
celery -A app.core.celery_app flower
```

### 服务访问

启动服务后，可以通过以下URL访问：

- API服务：http://localhost:8000
- Flower监控：http://localhost:5555（如已启动）

## API文档

启动服务后，可以通过以下URL访问API文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 认证与授权

### 认证方式

服务支持两种认证方式：

1. **Bearer令牌认证**：标准JWT令牌
   ```
   Authorization: Bearer <your_jwt_token>
   ```

2. **API密钥认证**：支持两种传递方式
   ```
   Authorization: ApiKey <your_api_key>
   ```
   或
   ```
   X-Api-Key: <your_api_key>
   ```

### API密钥类型

系统支持两种类型的API密钥：

- **系统级密钥**：有更高权限，可访问租户内所有用户数据
- **用户级密钥**：仅能访问特定用户的数据

### 权限机制

每个API端点都有特定的权限要求，格式为：`resource:action`，例如：

- `tasks:create` - 创建任务的权限
- `tasks:read` - 读取任务的权限
- `tasks:list` - 获取任务列表的权限

## 主要API接口

### 健康检查

```
GET /api/v1/health/
```

用于检查服务是否正常运行。

**响应示例：**
```json
{
  "success": true,
  "message": "Service is healthy. MongoDB: connected"
}
```

### 任务管理

#### 创建任务

```
POST /api/v1/tasks/
```

**所需权限：** `tasks:create`

**请求体：**

```json
{
  "model": "qwen-turbo",
  "provider": "aliyun",
  "parameters": {
    "prompt": "测试模型的最佳问题",
    "max_tokens": 800,
    "temperature": 0.7
  },
  "is_async": true
}
```

或者使用更高级的messages格式：

```json
{
  "model": "qwen-turbo",
  "provider": "aliyun",
  "parameters": {
    "messages": [
      {"role": "system", "content": "你是一个专业的教育顾问，擅长设计有效的测试问题"},
      {"role": "user", "content": "测试模型的最佳问题"}
    ],
    "max_tokens": 800,
    "temperature": 0.7
  },
  "is_async": true
}
```

关于`messages`格式：
- `system`角色：定义模型行为、风格和指导原则
- `user`角色：表示用户提问
- `assistant`角色：用于多轮对话中的历史回答

**响应示例：**
```json
{
  "success": true,
  "message": "任务已创建",
  "results": {
    "task_id": "684b9c6ca70fb02cc9fbd0b2"
  }
}
```

#### 获取任务状态

```
GET /api/v1/tasks/{task_id}/status/
```

**所需权限：** `tasks:read`

**响应示例：**
```json
{
  "success": true,
  "message": "获取任务状态成功",
  "results": {
    "task_id": "684b9c6ca70fb02cc9fbd0b2",
    "status": "completed",
    "created_at": "2025-06-13T11:01:12.345Z",
    "updated_at": "2025-06-13T11:01:15.678Z"
  }
}
```

#### 获取任务结果

```
GET /api/v1/tasks/{task_id}/result/
```

**所需权限：** `tasks:read`

**响应示例：**
```json
{
  "success": true,
  "message": "获取任务结果成功",
  "results": {
    "task_id": "684b9c6ca70fb02cc9fbd0b2",
    "status": "completed",
    "result": {
      "id": "07ebf3f1-55fb-94f6-8a5a-464d65b61f2d",
      "model": "qwen-turbo",
      "created": 1749785721,
      "choices": [
        {
          "index": 0,
          "message": {
            "role": "assistant",
            "content": "模型生成的回复内容..."
          },
          "finish_reason": "stop"
        }
      ],
      "usage": {
        "prompt_tokens": 12,
        "completion_tokens": 800,
        "total_tokens": 812
      }
    },
    "error": null
  }
}
```

#### 取消任务

```
POST /api/v1/tasks/{task_id}/cancel/
```

**所需权限：** `tasks:cancel`

**响应示例：**
```json
{
  "success": true,
  "message": "任务已取消",
  "results": {
    "task_id": "684b9c6ca70fb02cc9fbd0b2"
  }
}
```

#### 获取任务列表

```
GET /api/v1/tasks/
```

**所需权限：** `tasks:list`

**查询参数：**
- `page`: 页码，默认为1
- `page_size`: 每页数量，默认为10
- `status`: 按状态筛选（可选）
- `model`: 按模型筛选（可选）

**响应示例：**
```json
{
  "success": true,
  "message": "获取任务列表成功",
  "results": {
    "total": 42,
    "page": 1,
    "page_size": 10,
    "tasks": [
      {
        "task_id": "684b9c6ca70fb02cc9fbd0b2",
        "status": "completed",
        "model": "qwen-turbo",
        "created_at": "2025-06-13T11:01:12.345Z",
        "updated_at": "2025-06-13T11:01:15.678Z"
      },
      // ... 更多任务
    ]
  }
}
```

## 模型提供商

服务支持多种模型提供商，每个提供商支持不同的模型：

### 阿里云提供商 (aliyun)

支持的模型：
- `qwen-turbo`: 通义千问Turbo版
- `qwen-plus`: 通义千问Plus版
- `qwen-max`: 通义千问Max版
- `qwen-vl-max`: 通义千问视觉Max版
- `qwen-vl-plus`: 通义千问视觉Plus版

### DeepSeek提供商 (deepseek)

支持的模型：
- `deepseek-chat`: DeepSeek聊天模型
- `deepseek-reasoner`: DeepSeek推理模型

## 响应格式统一

无论调用哪个提供商的模型，返回结果都会被格式化为统一结构：

```json
{
  "id": "响应唯一标识符",
  "model": "使用的模型名称",
  "created": 时间戳,
  "choices": [
    {
      "index": 选项索引,
      "message": {
        "role": "assistant",
        "content": "模型生成的回复内容"
      },
      "finish_reason": "生成结束原因"
    }
  ],
  "usage": {
    "prompt_tokens": 提示词token数,
    "completion_tokens": 回复token数,
    "total_tokens": 总token数
  }
}
```

## 错误处理

所有API响应均遵循统一的格式：

### 成功响应
```json
{
  "success": true,
  "message": "操作成功描述",
  "results": { ... }
}
```

### 错误响应
```json
{
  "success": false,
  "message": "错误描述"
}
```

常见HTTP状态码：
- `401`: 未认证或认证失败
- `403`: 权限不足
- `404`: 资源不存在
- `500`: 服务器内部错误


## 部署

### 本地部署

1. 按照"快速开始"部分的说明设置环境并启动服务
2. 对于生产环境，建议使用 Gunicorn 或 Uvicorn 作为 WSGI 服务器

```bash
# 使用 Gunicorn 和 Uvicorn worker 启动
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 系统要求

- Python 3.10+
- MongoDB 4.4+
- Redis 6.0+

### 环境变量配置

在生产环境中，确保正确设置以下关键环境变量：

- `MONGODB_URI`: MongoDB连接URI
- `REDIS_URI`: Redis连接URI
- `AUTH_SERVICE_URL`: SciTigerCore认证服务URL
- `SERVICE_NAME`: 当前服务名称，用于权限验证
- `LOG_LEVEL`: 日志级别（默认为INFO）

详细配置请参考`app/core/config.py`文件。

## 权限系统

本服务集成了SciTigerCore的认证和权限系统，提供细粒度的权限控制。

## 权限控制机制

权限控制基于以下要素：

- **服务名称 (service)**: 当前微服务的名称
- **资源类型 (resource)**: 操作的资源类型，如"task"、"model"等
- **操作类型 (action)**: 对资源执行的操作，如"create"、"read"、"update"、"delete"等

## 单一来源权限管理

系统使用"单一来源原则"进行权限管理，只需要在API端点上添加装饰器或依赖项，无需维护单独的权限配置文件：

1. 在应用启动时，系统自动收集所有路由的权限要求
2. 中间件在请求处理早期根据请求路径查找对应的权限要求
3. 认证过程中自动进行权限验证

这种设计确保了：
- 权限定义只需要在一个地方（路由定义处）指定
- 避免了维护多个权限定义的复杂性和一致性问题
- 减少了对认证服务的重复请求

## 使用方式

在API端点中可以通过以下方式进行权限控制：

### 1. 使用装饰器

```python
from app.core.permissions import requires_permission

@router.post("/", response_model=TaskResponse)
@requires_permission(resource="task", action="create")
async def create_task(
    task_data: TaskCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    # 函数实现...
    pass
```

### 2. 使用依赖项

```python
from app.core.permissions import permission_required

@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(permission_required("task", "read"))
):
    # 函数实现...
    pass
```

### 3. 手动检查权限

```python
from app.core.permissions import check_permission

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    # 手动检查权限
    if not check_permission(request, "task", "update"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，无法更新任务"
        )
    
    # 函数实现...
    pass
```

## 权限检查流程

1. 应用启动时，收集所有路由的权限要求到全局映射表
2. 请求到达服务器时，中间件根据请求路径查找对应的权限要求
3. 中间件调用SciTigerCore的认证验证API，传递权限参数
4. SciTigerCore验证用户是否有权限执行请求的操作
5. 如果验证成功，请求继续处理；否则返回403错误

## 配置说明

配置通过环境变量或`.env`文件提供。主要配置项包括：

- `MONGODB_URI`: MongoDB连接URI
- `REDIS_URI`: Redis连接URI
- `AUTH_SERVICE_URL`: SciTigerCore认证服务URL
- `SERVICE_NAME`: 当前服务名称，用于权限验证



## 开发指南

### 项目结构

```
text-service/
├── app/                           # 应用主目录
│   ├── api/                       # API路由定义
│   │   ├── __init__.py            # API路由注册
│   │   ├── health.py              # 健康检查接口
│   │   └── tasks.py               # 任务管理接口
│   ├── core/                      # 核心功能模块
│   │   ├── __init__.py
│   │   ├── config.py              # 配置管理
│   │   ├── security.py            # 安全和认证
│   │   ├── celery_app.py          # Celery应用实例
│   │   └── logging.py             # 日志配置
│   ├── db/                        # 数据库相关
│   │   ├── __init__.py
│   │   ├── mongodb.py             # MongoDB连接和操作
│   │   └── repositories/          # 数据访问层
│   │       ├── __init__.py
│   │       └── task_repository.py # 任务数据访问
│   ├── models/                    # 数据模型
│   │   ├── __init__.py
│   │   ├── task.py                # 任务模型
│   │   └── user.py                # 用户模型
│   ├── schemas/                   # Pydantic模式
│   │   ├── __init__.py
│   │   ├── task.py                # 任务相关模式
│   │   └── common.py              # 通用模式
│   ├── services/                  # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── task_service.py        # 任务管理服务
│   │   └── model_providers/       # 模型提供商实现
│   │       ├── __init__.py
│   │       ├── base.py            # 基础接口
│   │       └── [provider_name].py # 具体提供商实现
│   ├── utils/                     # 工具函数
│   │   ├── __init__.py
│   │   └── helpers.py             # 辅助函数
│   │   └── response.py             # 统一响应格式
│   ├── worker/                    # 后台任务处理
│   │   ├── __init__.py
│   │   └── tasks.py               # Celery任务定义
│   ├── middleware/                # 中间件
│   │   ├── __init__.py
│   │   └── auth.py                # 认证中间件
│   └── main.py                    # 应用入口
├── .env.example                   # 环境变量示例
├── .gitignore                     # Git忽略文件
├── requirements.txt               # 依赖列表
└── README.md                      # 项目说明
```

### 添加新的模型提供商

1. 在`app/services/model_providers/`目录下创建新的提供商模块
2. 实现`ModelProvider`接口
3. 使用`register_provider`装饰器注册提供商

示例：

```python
from .base import ModelProvider
from . import register_provider

@register_provider
class NewProvider(ModelProvider):
    @property
    def provider_name(self) -> str:
        return "new_provider"
    
    # 实现其他必需方法
```