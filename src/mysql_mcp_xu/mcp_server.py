"""
mysql mcp server
xmq
"""
import asyncio
import re

import aiomysql
from fastmcp import FastMCP
from mysql_mcp_xu.config import load_config, PERMISSIONS
from mysql_mcp_xu.db_conn import MySQLConnectionPool, logger

config = load_config()
role = config.pop("role", "r")
mymcp = FastMCP("MySQL MCP Xu")
db_pool = MySQLConnectionPool(config)
db = config.get('db')


async def init_db():
    await db_pool.init_pool()


def extract_table_names(sql):
    # 匹配 FROM 和 JOIN 后面的表名
    from_tables = re.findall(r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE)
    join_tables = re.findall(r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE)

    tables = set(from_tables + join_tables)
    return tables


def generate_column_and_comment_sql(table_name):
    # 生成查询字段和备注的SQL语句
    sql = f"""
    SELECT 
        COLUMN_NAME AS column_name,
        COLUMN_COMMENT AS column_comment
    FROM 
        information_schema.COLUMNS
    WHERE 
        TABLE_SCHEMA = '{db}' AND 
        TABLE_NAME = '{table_name}';
    """
    return sql


# 获取pw_user表中罗丹的信息
async def _execute_single_sql(sql: str) -> str:
    """执行sql"""
    results = []
    column_comment = {}
    sql_list = [sql_.strip() for sql_ in sql.strip().split(';') if sql_.strip()]
    for sql in sql_list:
        first_word = sql.split(' ', 1)[0].upper()
        has_select = True if 'SELECT' == first_word else False
        if first_word not in PERMISSIONS[role]:
            results.append(f"当前角色：{role} 权限不足,无权执行操作:{sql}")
            continue
        if first_word == 'SELECT' and 'LIMIT' not in sql.upper():
            sql += " LIMIT 1000"

        try:
            async with await db_pool.get_connection() as conn:
                async with conn.cursor() as cursor:
                    if has_select:
                        table_names = extract_table_names(sql)
                        for table_name in table_names:
                            column_comment_sql = generate_column_and_comment_sql(table_name)
                            await cursor.execute(column_comment_sql)
                            res = await cursor.fetchall()
                            if res:
                                column_comment.update(dict(res))
                    await cursor.execute(sql)
                    if cursor.description:
                        columns = []
                        for desc in cursor.description:
                            column = desc[0]
                            comment = column_comment.get(column)
                            if comment:
                                column = f"{column}:{comment}"
                            columns.append(column)

                        rows = await cursor.fetchall()
                        if not rows:
                            results.append("无数据")
                            continue
                        formatted_rows = []
                        for row in rows:
                            formatted_row = ["NULL" if value is None else str(value) for value in row]
                            formatted_rows.append(",".join(formatted_row))

                        results.append("\n".join([",".join(columns)] + formatted_rows))
                    else:
                        await conn.commit()
                        results.append(f"执行成功。影响行数: {cursor.rowcount}")

        except Exception as e:
            results.append(f"sql执行失败: {str(e)}")

    if results:
        return "\n---\n".join(results)
    else:
        return "执行成功"


@mymcp.tool
async def execute_sql(sqls: str) -> str:
    """
    执行SQL语句(Execute SQL statements)
    :param sqls: SQL语句，多条语句用分号分隔
    :return: 执行结果的字符串表示
    """
    results = []

    try:
        sql_list = [sql.strip() for sql in sqls.strip().split(';') if sql.strip()]

        if not sql_list:
            return "没有有效的SQL语句"

        for sql in sql_list:
            try:
                result = await _execute_single_sql(sql)
                results.append(result)
            except Exception as e:
                error_msg = f"SQL执行失败: {sql[:50]}... - {str(e)}"
                logger.error(error_msg)
                results.append(error_msg)


        return "\n---\n".join(results) if results else "执行成功"

    except Exception as e:
        logger.error(f"SQL执行失败: {e}")
        return f"执行失败: {str(e)}"


@mymcp.tool
async def get_table_structure(table_names: str) -> str:
    """
    根据表名搜索数据库中对应的表字段(Search for the corresponding table fields in the database based on the table name)
    :param:
        table_names (str): 要查询的表名，多个表名以逗号分隔
    :return::
        - 返回表的字段名、字段注释等信息
        - 结果按表名和字段顺序排序
        - 结果以CSV格式返回，包含列名和数据
    """

    try:
        # 将输入的表名按逗号分割成列表
        table_names = [table_name.strip() for table_name in table_names.split(',')]
        # 构建IN条件
        table_condition = "','".join(table_names)
        sql = "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_COMMENT "
        sql += f"FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = '{db}' "
        sql += f"AND TABLE_NAME IN ('{table_condition}') ORDER BY TABLE_NAME, ORDINAL_POSITION;"
        return await _execute_single_sql(sql)
    except Exception as e:
        return f"数据库查询失败: {str(e)}', {table_names}, {sql}"


@mymcp.tool
async def get_table_indexes(table_names: str) -> str:
    """
    获取指定表的索引信息(Get the index information of the specified table.)
    :param
        table_names:要查询的表名，多个表名以逗号分隔
    :return:
        - 返回表的索引名、索引字段、索引类型等信息
        - 结果按表名、索引名和索引顺序排序
        - 结果以CSV格式返回，包含列名和数据
    """

    # 将输入的表名按逗号分割成列表
    table_names = [table_name.strip() for table_name in table_names.split(',')]
    # 构建IN条件
    table_condition = "','".join(table_names)
    try:
        sql = "SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX, NON_UNIQUE, INDEX_TYPE "
        sql += f"FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = '{db}' "
        sql += f"AND TABLE_NAME IN ('{table_condition}') ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;"
        return await _execute_single_sql(sql)
    except Exception as e:
        return f"数据库查询失败: {str(e)}"


@mymcp.tool
async def search_table_by_name(table_name: str) -> str:
    """
    根据表的名称或表的注释描述搜索数据库中对应的表名(Search for the corresponding table name in
     the database based on the table's name or the description in its comment.)
    :param:
        table_name (str): 表中文名或表描述
    :return::
        - 返回匹配的表名
        - 匹配结果按匹配度排序
        - 匹配结果以CSV格式返回，包含列名和数据
    """

    try:
        sql = "SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_COMMENT "
        sql += f"FROM information_schema.TABLES "
        sql += f"WHERE TABLE_SCHEMA = '{db}' AND TABLE_COMMENT LIKE '%{table_name}%';"
        return await _execute_single_sql(sql)
    except Exception as e:
        return f"数据库查询失败: {str(e)}"


@mymcp.tool
async def get_database_info() -> str:
    """
    获取数据库基本信息(Get basic database information)
    """
    try:
        info_sql = """
        SELECT 
            'Database' as info_type, 
            DATABASE() as value
        UNION ALL
        SELECT 
            'Version' as info_type, 
            VERSION() as value
        UNION ALL
        SELECT 
            'Current User' as info_type, 
            USER() as value
        UNION ALL
        SELECT 
            'Connection ID' as info_type, 
            CONNECTION_ID() as value
        """

        return await _execute_single_sql(info_sql)
    except Exception as e:
        return f"获取数据库信息失败: {str(e)}"


@mymcp.tool
async def get_mysql_health() -> str:
    """
    获取当前mysql的健康状态(Obtain the current health status of MySQL)
    """
    try:
        status_sql = """
        SHOW GLOBAL STATUS WHERE Variable_name IN (
            'Uptime',
            'Threads_connected',
            'Threads_running',
            'Queries',
            'Open_files',
            'Open_tables',
            'Innodb_buffer_pool_read_requests',
            'Innodb_buffer_pool_reads',
            'Key_read_requests',
            'Key_reads',
            'Created_tmp_disk_tables',
            'Handler_read_rnd_next',
            'Aborted_clients',
            'Aborted_connects'
        )
        """

        variables_sql = """
        SHOW GLOBAL VARIABLES WHERE Variable_name IN (
            'innodb_buffer_pool_size',
            'max_connections',
            'table_open_cache',
            'query_cache_size',
            'key_buffer_size',
            'version'
        )
        """

        status_result = await _execute_single_sql(status_sql)
        variables_result = await _execute_single_sql(variables_sql)

        pool_status = f"连接池状态: {'正常' if db_pool.pool and not db_pool.pool.closed else '异常'}"
        if db_pool.pool and not db_pool.pool.closed:
            pool_status += f" (大小: {db_pool.pool.size}, 空闲: {db_pool.pool.freesize})"

        return f"=== MySQL健康状态 ===\n{pool_status}\n\n=== 系统状态 ===\n{status_result}\n\n=== 系统变量 ===\n{variables_result}"

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return f"健康检查失败: {str(e)}"


@mymcp.tool
async def get_database_schema() -> str:
    """
    获取数据库架构信息(Get database schema information)
    """
    try:
        # 获取所有表
        tables_sql = "SHOW TABLES"
        tables_result = await _execute_single_sql(tables_sql)

        # 获取所有视图
        views_sql = "SHOW FULL TABLES WHERE Table_type = 'VIEW'"
        views_result = await _execute_single_sql(views_sql)

        # 获取数据库大小
        size_sql = """
        SELECT 
            table_schema as '数据库',
            ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as '大小(MB)',
            COUNT(*) as '表数量'
        FROM information_schema.tables 
        WHERE table_schema = DATABASE()
        GROUP BY table_schema
        """
        size_result = await _execute_single_sql(size_sql)

        return f"=== 数据库概览 ===\n{size_result}\n\n=== 表列表 ===\n{tables_result}\n\n=== 视图列表 ===\n{views_result}"
    except Exception as e:
        return f"获取数据库架构失败: {str(e)}"


@mymcp.tool
async def analyze_table_stats(table_name: str) -> str:
    """
    分析表统计信息和列统计信息(Analyze table statistics and column statistics)
    :param table_name: 表名
    :return: 表统计信息
    """
    try:
        # 获取表的基本统计信息
        stats_sql = f"""
        SELECT 
            TABLE_NAME as '表名',
            TABLE_ROWS as '行数',
            ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as '大小(MB)',
            ROUND(DATA_LENGTH / 1024 / 1024, 2) as '数据大小(MB)',
            ROUND(INDEX_LENGTH / 1024 / 1024, 2) as '索引大小(MB)',
            ENGINE as '存储引擎',
            TABLE_COLLATION as '字符集'
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() AND table_name = '{table_name}'
        """

        # 获取列统计信息
        columns_sql = f"""
        SELECT 
            COLUMN_NAME AS '列名',
            COLUMN_COMMENT AS '列备注',
            DATA_TYPE AS '数据类型',
            IS_NULLABLE AS '允许NULL',
            COLUMN_DEFAULT AS '默认值',
            COLUMN_KEY AS '键类型',     
            EXTRA AS '额外信息',
        FROM 
            information_schema.columns 
        WHERE 
            table_schema = DATABASE() 
            AND table_name = '{table_name}'
        ORDER BY 
            ORDINAL_POSITION;
        """

        stats_result = await _execute_single_sql(stats_sql)
        columns_result = await _execute_single_sql(columns_sql)

        return f"=== 表统计信息 ===\n{stats_result}\n\n=== 列信息 ===\n{columns_result}"
    except Exception as e:
        return f"分析表统计信息失败: {str(e)}"


@mymcp.tool
async def get_process_list() -> str:
    """
    获取当前进程列表(Get current process list)
    """
    try:
        process_sql = """
        SELECT 
            ID as '进程ID',
            USER as '用户',
            HOST as '主机',
            DB as '数据库',
            COMMAND as '命令',
            TIME as '时间(秒)',
            STATE as '状态',
            LEFT(INFO, 100) as 'SQL语句'
        FROM information_schema.processlist 
        WHERE COMMAND != 'Sleep'
        ORDER BY TIME DESC
        """

        return await _execute_single_sql(process_sql)
    except Exception as e:
        return f"获取进程列表失败: {str(e)}"


@mymcp.tool
async def check_table_constraints(table_name: str) -> str:
    """
    检查表约束信息(Check table constraints)
    :param table_name: 表名
    :return: 约束信息
    """
    try:
        # 获取外键约束
        fk_sql = f"""
        SELECT 
            CONSTRAINT_NAME as '约束名',
            COLUMN_NAME as '列名',
            REFERENCED_TABLE_NAME as '引用表',
            REFERENCED_COLUMN_NAME as '引用列',
            UPDATE_RULE as '更新规则',
            DELETE_RULE as '删除规则'
        FROM information_schema.key_column_usage 
        WHERE table_schema = DATABASE() 
        AND table_name = '{table_name}' 
        AND REFERENCED_TABLE_NAME IS NOT NULL
        """

        # 获取检查约束（MySQL 8.0+）
        check_sql = f"""
        SELECT 
            CONSTRAINT_NAME as '约束名',
            CHECK_CLAUSE as '检查条件'
        FROM information_schema.check_constraints 
        WHERE constraint_schema = DATABASE() 
        AND table_name = '{table_name}'
        """

        fk_result = await _execute_single_sql(fk_sql)

        try:
            check_result = await _execute_single_sql(check_sql)
            return f"=== 外键约束 ===\n{fk_result}\n\n=== 检查约束 ===\n{check_result}"
        except:
            # 如果不支持检查约束，只返回外键约束
            return f"=== 外键约束 ===\n{fk_result}"

    except Exception as e:
        return f"获取表约束信息失败: {str(e)}"


async def mcp_run(mode='stdio'):
    try:
        await init_db()
        import sys
        if len(sys.argv) > 1:
            mode = sys.argv[1]

        if mode == 'sh':
            await mymcp.run_async(transport="streamable-http", host="0.0.0.0", port=9009)
        elif mode == 'sse':
            await mymcp.run_async(transport="sse", host="0.0.0.0", port=9009)
        else:
            await mymcp.run_async(transport="stdio")

    except Exception as e:
        logger.error(f"MCP server启动失败: {e}")
        raise
    finally:
        await db_pool.close()


if __name__ == "__main__":
    asyncio.run(mcp_run())
