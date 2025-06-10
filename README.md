[![PyPI Version](https://img.shields.io/pypi/v/mysql-mcp-xu)](https://pypi.org/project/mysql-mcp-xu)
[![PyPI Downloads](https://static.pepy.tech/badge/mysql-mcp-xu)](https://pepy.tech/projects/mysql-mcp-xu)
# MySQL MCP Xu

## 项目简介
MySQL MCP Xu 是一个基于 FastMCP 的 MySQL MCP Server项目，提供了一个安全、高效的接口来执行 SQL 操作。该项目支持多种权限控制（读、写、管理员），并通过工具函数实现了表结构查询、索引信息获取、健康状态监控等功能。

## 目录结构
```
.
├── src
│   └── mysql_mcp_xu
│       ├── __init__.py
│       ├── config.py
│       └── mcp_server.py
├── README.md
└── pyproject.toml
```

## 快速开始
1. 安装：`pip install mysql-mcp-xu`
2. 执行命令的目录创建一个 `.env` 文件，内容如下：
```bash
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database
MYSQL_ROLE=r # 可选值: r, w, a
MYSQL_MAXSIZE=2 # 可选值 连接池最大值
```
3. 启动命令：
   - STDIO：uv run -m mysql_mcp_xu.mcp_server 
   - Streamable HTTP： uv run -m mysql_mcp_xu.mcp_server sh
   - SSE: uv run -m mysql_mcp_xu.mcp_server sse
4. 使用 MCP 客户端连接服务并执行 SQL 操作。

## 功能特性
- **SQL 执行**：支持执行多条 SQL 语句，并返回结果。
- **权限控制**：根据角色（读、写、管理员）限制 SQL 操作。
- **表结构查询**：获取指定表的字段名、字段注释等信息。
- **索引信息获取**：获取指定表的索引名、索引字段、索引类型等信息。
- **健康状态监控**：获取 MySQL 的健康状态，包括连接数、查询次数、缓冲池使用情况等。


## 权限控制
权限控制通过 `PERMISSIONS` 字典实现，支持以下角色：
- `r`：只读权限，允许执行 `SELECT`, `SHOW`, `DESCRIBE`, `EXPLAIN`, `USE` 操作。
- `w`：读写权限，允许执行 `SELECT`, `SHOW`, `DESCRIBE`, `EXPLAIN`, `INSERT`, `UPDATE`, `DELETE`, `USE` 操作。
- `a`：管理员权限，允许执行所有操作，包括 `CREATE`, `ALTER`, `DROP`, `TRUNCATE` 等。

## 工具函数
- `execute_sql`: 执行 SQL 语句并返回结果,SELECT语句没有LIMIT时，自动在sql后加LIMIT 1000。
- `get_table_structure`: 获取指定表的字段信息。
- `get_table_indexes`: 获取指定表的索引信息。
- `search_table_by_chinese`: 根据表中文名或表描述搜索数据库中对应的表名。
- `get_mysql_health`: 获取 MySQL 的健康状态。
- `get_database_info`: 获取数据库基本信息
- `get_database_schema`: 获取数据库架构信息
- `analyze_table_stats`: 分析表统计信息和列统计信息
- `get_process_list`: 获取当前进程列表
- `check_table_constraints`: 检查表约束信息

## 部署方式

### 使用 uvx 部署

在 MCP 配置文件中添加如下配置，以使用 `uvx` 部署 MySQL MCP Xu 服务：
#### STDIO

```json
{
  "mcpServers": {
    "mysql-mcp-xu": {
      "command": "uvx",
      "args": [
        "mysql-mcp-xu"
      ],
      "env": {
         "MYSQL_HOST": "", 
         "MYSQL_PORT": 3306,
         "MYSQL_USER": "",
         "MYSQL_PASSWORD": "",
         "MYSQL_DATABASE": "",
         "MYSQL_ROLE": "r",
         "MYSQL_MAXSIZE": 2
      }
    }
  }
}
```
#### Streamable HTTP

```json
{
  "mcpServers": {
    "mysql-mcp-xu": {
      "name": "mysql-mcp-xu",
      "type": "streamableHttp",
      "description": "",
      "isActive": true,
      "url": "http://localhost:9009/mcp"
    }
  }
}
```
#### SSE

```json
{
  "mcpServers": {
    "mysql-mcp-xu": {
      "name": "mysql-mcp-xu",
      "description": "",
      "isActive": true,
      "url": "http://localhost:9009/sse"
    }
  }
}
```
### 使用 uv 部署
```json
{
  "mcpServers": {
    "mysql-mcp-xu": {
      "command": "uv",
      "args": [
        "--directory",
        "D:/mysql-mcp-xu/src/mysql_mcp_xu",
        "run",
        "-m",
        "mcp_server"
      ]
    }
  }
}
```
#### Streamable HTTP
```json
{
  "mcpServers": {
    "mysql-mcp-xu": {
      "command": "uv",
      "args": [
        "--directory",
        "D:/mysql-mcp-xu/src/mysql_mcp_xu",
        "run",
        "-m",
        "mcp_server",
        "sh"
      ]
    }
  }
}
```

#### sse
```json
{
  "mcpServers": {
    "mysql-mcp-xu": {
      "command": "uv",
      "args": [
        "--directory",
        "D:/mysql-mcp-xu/src/mysql_mcp_xu",
        "run",
        "-m",
        "mcp_server",
        "sse"
      ]
    }
  }
}