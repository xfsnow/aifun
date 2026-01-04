import datetime
import pymysql
import os

from pymysql.converters import escape_string

class Table:
    JOIN_INNER = 'INNER'
    JOIN_LEFT = 'LEFT'
    JOIN_RIGHT = 'RIGHT'
    JOIN_FULL = 'FULL'
    JOIN_CROSS = 'CROSS'

    INSERT_REPLACE = 'replace'
    INSERT_IGNORE = 'ignore'
    INSERT_UPDATE = 'update'

    ORDER_ASC = 'ASC'
    ORDER_DESC = 'DESC'

    def __init__(self, table, debug=False):
        self.debug = debug
        self.m_table = table
        self.m_sqljoin = ""
        self.m_sqlwhere = ""
        self.m_sqlorder = ""
        self.m_sqlgroup = ""
        self.m_sqllimit = ""

        mysqlHost = os.environ.get("MYSQL_HOST") or 'localhost'
        mysqlUser = os.environ.get("MYSQL_USER") or 'root'
        mysqlPassword = os.environ.get("MYSQL_PASSWORD") or ''
        mysqlDatabase = os.environ.get("MYSQL_DATABASE") or 'test'
        env = os.environ.get("FLASK_ENV")
        
        jsonSsl = {'ca': 'models/DigiCertGlobalRootCA.crt.pem'} if env != 'development' else None
        print(f"Connecting to MySQL database at {mysqlHost} as user {mysqlUser} in {env} environment.")
        connection = pymysql.connect(
                host=mysqlHost,
                user=mysqlUser,
                password=mysqlPassword,
                database=mysqlDatabase,
                autocommit=True,
                ssl=jsonSsl
            )
        self.cursor = connection.cursor()
        self.m_errorstr = ""

    def clear_error(self):
        self.m_errorstr = ""

    def set_error(self, error_str):
        self.m_errorstr = error_str

    # SQL 转义
    def sql_escape(self, value):
        return escape_string(value)

    def get_table(self):
        return self.m_table

    def select(self, *fields):
        if not fields:
            fields = '*'
        else:
            fields = ", ".join(fields)
        self.m_sqlfields = fields
        return self

    def join(self, table, on_left_table, on_right_table, join_type=JOIN_INNER):
        self.m_sqljoin = f" {join_type} JOIN {table} ON {on_left_table} = {on_right_table}"
        return self

    def where(self, key, operator, value, conjunction='WHERE'):
        self.clear_error()
        # operator统一转换成大写
        operator = operator.upper()
        allowed_operators = ['=', '>', '<', '<>', '!=', '>=', '<=','IS', 'IS NOT', 'IN', 'LIKE', 'NOT IN', 'REGEXP']
        if operator not in allowed_operators:
            self.set_error(f"(SQL error: field[{key}]'s {operator} is not a valid operator.")
        if operator in ['IN', 'NOT IN']:
            value = f"({', '.join([f'\'{self.sql_escape(v)}\'' for v in value])})"
            condition = f" ({key} {operator} {value}) "
        else:
            value = 'NULL' if value is None else f"'{self.sql_escape(value)}'"
            condition = f" ({key} {operator} {value}) "
        self.m_sqlwhere += f" {conjunction} {condition}"
        return self

    def and_where(self, key, operator, value):
        return self.where(key, operator, value, 'AND')

    def or_where(self, key, operator, value):
        return self.where(key, operator, value, 'OR')

    def order_by(self, *fields):
        self.m_sqlorder = " ORDER BY "
        if len(fields) == 1:
            self.m_sqlorder += f"{fields[0]} ASC"
        elif len(fields) > 1:
            for i in range(0, len(fields), 2):
                # 检查是否还有下一个元素（即排序方向）
                if i+1 < len(fields):
                    self.m_sqlorder += f"{fields[i]} {fields[i+1]},"
                else:
                    # 如果只剩一个元素，使用默认的ASC排序
                    self.m_sqlorder += f"{fields[i]} ASC,"
            self.m_sqlorder = self.m_sqlorder.rstrip(',')
        return self

    def group_by(self, fields):
        self.m_sqlgroup = f" GROUP BY {fields}"
        return self

    def limit(self, start, length=None):
        if length is None:
            self.m_sqllimit = f" LIMIT {start}"
        else:
            self.m_sqllimit = f" LIMIT {start}, {length}"
        return self

    def query(self, sql):
        self.m_sql = sql
        self.clear_error()
        # print(sql)

        try:
            if self.debug:
                print(f"SQL: {sql}")
                time_begin = datetime.datetime.now().timestamp()
            self.cursor.execute(sql)
            if self.debug:
                elapsed_time = (datetime.datetime.now().timestamp() - time_begin) * 1000
                formatted_time = f"{elapsed_time:.4f} ms"
                print(f"SQL run time: {formatted_time}")
        except pymysql.err.InterfaceError as e:
            print(f"SQL execution error: {e}")
        except pymysql.err.ProgrammingError as e:
            print(f"SQL syntax error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

        self.m_sqlwhere = ""
        self.m_sql = ""
        self.m_sqlfields = ""
        return self

    def get(self):
        self.clear_error()
        if self.m_sqlfields:
            sql = f"SELECT {self.m_sqlfields} FROM {self.m_table}{self.m_sqljoin}{self.m_sqlwhere}{self.m_sqlorder}{self.m_sqllimit}"
            # 执行查询
            self.cursor.execute(sql)
            result = self.cursor.fetchall()
            # fetchall() 返回的一个是元组的列表，转换为字典的列表
            field_names = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(field_names, row)) for row in result]
            # 数据库表中某字段值为空时，to_dict()会将其转换为None，把它改成空字符串
            for record in result:
                for key, value in record.items():
                    if value is None:
                        record[key] = ''
        else:
            result = []
            
        # 清除查询条件
        self.m_sqlwhere = ""
        self.m_sql = ""
        self.m_sqlfields = ""
        return result

    def insert(self, data, on_duplicate=INSERT_IGNORE):
        self.clear_error()
        fields = list(data[0].keys())
        values = []
        for row in data:
            # 对于每一行数据，转换成 SQL 语句的格式
            # 如果值为 None 或者空字符串，则转换成 NULL
            # 如果值为日期，则转换成字符串格式
            # 如果值为字符串，则转换成 SQL 语句的格式
            # 如果值为数字，则直接使用
            value = []
            for key in fields:
                val = row[key]
                if val is None or val == '':
                    value.append('NULL')
                elif isinstance(val, str):
                    value.append(f"'{self.sql_escape(val)}'")
                elif isinstance(val, (int, float)):
                    value.append(str(val))
                elif isinstance(val, (datetime.date)):
                    value.append("'"+ val.strftime('%Y-%m-%d')+"'")
                elif isinstance(val, (datetime.datetime)):
                    value.append("'"+ val.strftime('%Y-%m-%d %H:%M:%S')+"'")
                else:
                    value.append(f"'{self.sql_escape(str(val))}'")
            values.append(f"({', '.join(value)})")
        sql = f"INSERT INTO {self.m_table} ({', '.join(fields)}) VALUES {', '.join(values)}"
        if on_duplicate == self.INSERT_REPLACE:
            sql = f"REPLACE INTO {self.m_table} ({', '.join(fields)}) VALUES {', '.join(values)}"
        elif on_duplicate == self.INSERT_IGNORE:
            sql = f"INSERT IGNORE INTO {self.m_table} ({', '.join(fields)}) VALUES {', '.join(values)}"
        elif on_duplicate == self.INSERT_UPDATE:
            update_fields = [f"{field}=VALUES({field})" for field in fields]
            sql += f" ON DUPLICATE KEY UPDATE {', '.join(update_fields)}"
        self.query(sql)
        return self.cursor.rowcount

    def add(self, data, on_duplicate=INSERT_IGNORE):
        return self.insert([data], on_duplicate)

    def update(self, data):
        self.clear_error()
        fields = [f"{key} = {'NULL' if (val is None or val=='') else f'\'{self.sql_escape(val)}\''}" for key, val in data.items()]
        sql = f"UPDATE {self.m_table} SET {', '.join(fields)}{self.m_sqlwhere}"
        if not self.m_sqlwhere:
            err = f"[SQL: {sql}, errors: WHERE condition is required to execute UPDATE.]"
            self.set_error(err)
            print(err)
            return False
        self.query(sql)
        return self.cursor.rowcount