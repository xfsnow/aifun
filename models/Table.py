import os
import pymysql
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

    def __init__(self, table):
        self.m_table = table
        self.m_sqljoin = ""
        self.m_sqlwhere = ""
        self.m_sqlorder = ""
        self.m_sqlgroup = ""
        self.m_sqllimit = ""

        mysqlHost = os.environ.get("MYSQL_HOST")
        mysqlUser = os.environ.get("MYSQL_USER")
        mysqlPassword = os.environ.get("MYSQL_PASSWORD")
        mysqlDatabase = os.environ.get("MYSQL_DATABASE")
        env = os.environ.get("FLASK_ENV")

        key = f"{mysqlHost}_{mysqlUser}_{mysqlDatabase}"
        if not hasattr(Table, 'connection'):
            Table.connection = {}
        if key not in Table.connection:
            Table.connection[key] = pymysql.connect(
                host=mysqlHost,
                user=mysqlUser,
                password=mysqlPassword,
                database=mysqlDatabase,
                autocommit=True,
                ssl={'ca': 'models/DigiCertGlobalRootCA.crt.pem'} if env != 'development' else None
            )
        connection = Table.connection[key]
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
        allowed_operators = ['is', 'is not', 'in', 'like', 'not in', '=', '>', '<', '<>', '!=', '>=', '<=']
        if operator not in allowed_operators:
            self.set_error(f"(SQL error: field[{key}]'s {operator} is not a valid operator.")
            return False
        if operator in ['in', 'not in']:
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
                self.m_sqlorder += f"{fields[i]} {fields[i+1]},"
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
        print(sql)
        self.cursor.execute(sql)
        self.m_sqlwhere = ""
        self.m_sql = ""
        self.m_sqlfields = ""
        return self

    def get(self):
        self.clear_error()
        if self.m_sqlfields:
            sql = f"SELECT {self.m_sqlfields} FROM {self.m_table}{self.m_sqljoin}{self.m_sqlwhere}{self.m_sqlorder}{self.m_sqllimit}"
            self.query(sql)

        result = self.cursor.fetchall()
        # fetchall() 返回的一个是元组的列表，转换为字典的列表
        field_names = [desc[0] for desc in self.cursor.description]
        result = [dict(zip(field_names, row)) for row in result]
        # 数据库表中某字段值为空时，to_dict()会将其转换为None，把它改成空字符串
        for record in result:
            for key, value in record.items():
                if value is None:
                    record[key] = ''
        self.m_sqlwhere = ""
        self.m_sql = ""
        self.m_sqlfields = ""
        return result

    def insert(self, data, on_duplicate=INSERT_IGNORE):
        self.clear_error()
        fields = list(data[0].keys())
        values = []
        for row in data:
            value = [f"'{self.sql_escape(val)}'" if (val is not None and val != "") else 'NULL' for val in row.values()]
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