"""
mysql mcp server
xmq
"""
import asyncio
from fastmcp import FastMCP
from mysql.connector import connect, Error
from mysql_mcp_xu.config import load_config, PERMISSIONS

config = load_config()
role = config.pop("role", "r")
mymcp = FastMCP("MySQL MCP Xu")


def get_connection():
    """
    连接数据库
    """
    return connect(**config)


def _execute_sql(sqls: str) -> str:
    results = []
    try:
        conn = get_connection()
        # cursor = conn.cursor(dictionary=True)
        cursor = conn.cursor()
        # 处理多条SQL语句
        sql_list = [sql.strip() for sql in sqls.strip().split(';') if sql.strip()]
        for sql in sql_list:
            first_word = sql.split(' ', 1)[0].upper()
            if first_word not in PERMISSIONS[role]:
                results.append(f"当前角色：{role} 权限不足,无权执行操作:{sql}")
                continue
            if first_word == 'SELECT' and 'LIMIT' not in sql.upper():
                sql += " LIMIT 1000"
            try:
                cursor.execute(sql)

                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()

                    # 将每一行的数据转换为字符串，特殊处理None值
                    formatted_rows = []
                    for row in rows:
                        formatted_row = ["NULL" if value is None else str(value) for value in row]
                        formatted_rows.append(",".join(formatted_row))

                    # 将列名和数据合并为CSV格式
                    results.append("\n".join([",".join(columns)] + formatted_rows))
                else:
                    conn.commit()
                    results.append(f"执行成功。影响行数: {cursor.rowcount}")
            except Error as e:
                results.append(f"sql执行失败: {str(e)}")

        return "\n---\n".join(results) if results else "执行成功"

    except Error as e:
        return f"sql执行失败: {str(e)}"
    finally:
        cursor.close()
        conn.close()


@mymcp.tool
def execute_sql(sqls: str) -> str:
    """
    在MySql数据库上执行";"分割的SQL语句并返回结果(Execute the SQL
     statements separated by ";" on the MySql database and return the results)
    :param:
        sqls (str): SQL语句，多个SQL语句以";"分隔
    :return::
        结果以CSV格式返回，包含列名和数据
    """

    return _execute_sql(sqls)

@mymcp.tool
def get_table_structure(table_names: str) -> str:
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
        sql += f"FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = '{config['database']}' "
        sql += f"AND TABLE_NAME IN ('{table_condition}') ORDER BY TABLE_NAME, ORDINAL_POSITION;"
        return _execute_sql(sql)
    except Exception as e:
        return f"数据库查询失败: {str(e)}"


@mymcp.tool
def get_table_indexes(table_names: str) -> str:
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
        sql += f"FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = '{config['database']}' "
        sql += f"AND TABLE_NAME IN ('{table_condition}') ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;"
        return _execute_sql(sql)
    except Exception as e:
        return f"数据库查询失败: {str(e)}"


@mymcp.tool
def search_table_by_chinese(table_name: str) -> str:
    """
    根据表的中文名或表的描述搜索数据库中对应的表名(Search for the corresponding table name
    in the database based on the Chinese name of the table or the description of the table)
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
        sql += f"WHERE TABLE_SCHEMA = '{config['database']}' AND TABLE_COMMENT LIKE '%{table_name}%';"
        return _execute_sql(sql)
    except Exception as e:
        return f"数据库查询失败: {str(e)}"


@mymcp.tool
def get_mysql_health() -> str:
    """
    获取当前mysql的健康状态(Obtain the current health status of MySQL)
    """

    try:
        # 查询系统状态变量
        sql = """
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
        );"""
        sql += """SHOW GLOBAL VARIABLES WHERE Variable_name IN (
            'innodb_buffer_pool_size',
            'max_connections',
            'table_open_cache',
            'query_cache_size',
            'key_buffer_size'
        );"""
        return _execute_sql(sql)
    except Exception as e:
        return f"数据库查询失败: {str(e)}"


def mcp_run(mode='stdio'):
    import sys
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    if mode == 'sh':
        mymcp.run(transport="streamable-http", host="0.0.0.0", port=9009)
    elif mode == 'sse':
        mymcp.run(transport="sse", host="0.0.0.0", port=9009)
    else:
        mymcp.run(transport="stdio")


if __name__ == "__main__":
    mcp_run()
