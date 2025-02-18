import os
from sqlalchemy import create_engine

class SqlHelper:

    # 创建数据库引擎
    # autocommit: 是否自动提交事务
    # debug: 是否打印调试信息
    # 返回值：create_engine
    @staticmethod
    def createDbEngine(autocommit=False,debug=False) -> create_engine:
        mysqlHost = os.environ.get("MYSQL_HOST")
        mysqlUser = os.environ.get("MYSQL_USER")
        mysqlPassword = os.environ.get("MYSQL_PASSWORD")
        mysqlDatabase = os.environ.get("MYSQL_DATABASE")
        strMysqlConn = 'mysql+pymysql://'+mysqlUser+':'+mysqlPassword+'@'+mysqlHost+'/'+mysqlDatabase
        engine = create_engine(strMysqlConn, echo=debug)
        if autocommit:
            # Session 级别的 autocommit 已经没有了，现在需要在 create_engine 时指定 isolation_level 来实现
            engine = engine.execution_options(isolation_level="AUTOCOMMIT")

        return engine