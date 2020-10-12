#coding:utf8
# Embedded file name: /work/build/source/athena/utils/db/db_mysql.py
"""
用于MySQL数据库相关的一些方法
   
"""
import db
import MySQLdb
import datetime


# duanyifei 2016-5-23
class Cursor(object):
    '''重新封装cursor使得可以自动捕获mysql连接超时错误并重新连接'''
    def __init__(self, mysql_conn, setting_dict, **kwargs):
        self.cursor = mysql_conn.cursor(**kwargs)
        self.setting_dict = setting_dict
        self.conn = mysql_conn
        self.kwargs = kwargs

    def __getattr__(self, name):
        '''不存在的属性调用原cursor'''
        return getattr(self.cursor, name)

    def execute(self, sql, args=None):
        try:
            result = self.cursor.execute(sql, args=args)
        except MySQLdb.OperationalError as e:
            #捕获超时异常
            err_args = e.args
            code = err_args[0]
            if code in (2006, 2013):
                #重连
                mysql_conn = self.get_new_conn()
                self.cursor = mysql_conn.cursor(**self.kwargs)
                self.conn = mysql_conn
                return self.execute(sql, args=args)
            else:
                raise MySQLdb.OperationalError(*err_args)
        return result

    def get_new_conn(self):
        db_user = self.setting_dict['username']
        db_passwd = self.setting_dict['password']
        db_host = self.setting_dict['host']
        db_port = self.setting_dict['port']
        if db_port is None:
            db_port = 3306
        db_default = self.setting_dict['db']
        try:
            conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_passwd, db=db_default)
            conn.autocommit(True)
            conn.query("set names 'utf8'")
        except MySQLdb.MySQLError as e:
            raise Exception('Mysql 数据库连接错误：%s, %s' % (e, self.setting_dict))
            return (None, None)
        return conn
# duanyifei 2016-5-23


class MySQLOpt(db.DbOpt):
    connection_list = {}

    def __init__(self, setting_dict):
        db.DbOpt.__init__(self, setting_dict)
        self.key = repr(setting_dict)
        if self.key not in MySQLOpt.connection_list.keys():
            self.cursor = self.GetCursor()
            MySQLOpt.connection_list[self.key] = self.cursor
        else:
            self.cursor = MySQLOpt.connection_list[self.key]
        self.sql = {}
        self.clear()

    @property
    def conn(self):
        self._conn = self.cursor.conn
        return self._conn

    def clear(self):
        """
        清空where和tables等设置，以便于下次执行sql后重新生成
        """
        self.sql['where'] = ''
        self.sql['tables'] = ''
        self.sql['fields'] = ''
        self.sql['limit'] = (0, 0)
        self.sql['order'] = {}

    def GetCursor(self):
        """
        mysql获取cursor
        """
        db_user = self.setting_dict['username']
        db_passwd = self.setting_dict['password']
        db_host = self.setting_dict['host']
        db_port = self.setting_dict['port']
        if db_port is None:
            db_port = 3306
        db_default = self.setting_dict['db']
        try:
            conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_passwd, db=db_default)
            conn.autocommit(True)
            conn.query("set names 'utf8'")
        except MySQLdb.MySQLError as e:
            raise Exception('Mysql 数据库连接错误：%s, %s' % (e, self.setting_dict))
            return (None, None)
        
        cursor = Cursor(conn, self.setting_dict, cursorclass=MySQLdb.cursors.DictCursor)
        
        return cursor

    def where(self, condition):
        self.sql['where'] = condition
        return self

    def get_where(self):
        if self.sql['where'] == '':
            return ''
        else:
            return ' where ' + self.sql['where']

    def table(self, table_str):
        self.sql['tables'] = table_str
        return self

    def delete(self):
        if self.sql['tables'] == '':
            self.clear()
            raise Exception('缺少table名称')
        self.cursor.execute('delete from ' + self.sql['tables'] + self.get_where())
        self.clear()

    def add(self, data_dicts):
        if self.sql['tables'] == '':
            raise Exception('缺少table名称')
        import types
        if type(data_dicts) is types.DictType:
            tmp = data_dicts
            data_dicts = []
            data_dicts.append(tmp)
        elif type(data_dicts) is not types.ListType:
            self.clear()
            raise Exception('输入变量必须为字典或者字典列表')
        row_count = len(data_dicts)
        if row_count == 0:
            self.clear()
            raise Exception('数据为空')
        keys = data_dicts[0].keys()
        column_count = len(keys)
        if column_count == 0:
            self.clear()
            raise Exception('数据为空')
        sql = 'insert into %s (%s) ' % (self.sql['tables'], ','.join(keys))
        all_row_list = []
        for row_dict in data_dicts:
            row_list = []
            for value in row_dict.values():
                if type(value) == type('some'):
                    row_list.append("'%s'" % value)
                elif type(value) == type(None):
                    row_list.append('null')
                elif type(value) == type(datetime.datetime.now()):
                    row_list.append("'%s'" % value)
                elif type(value) == type(datetime.date.today()):
                    row_list.append("'%s'" % value)
                else:
                    row_list.append(str(value))

            one_row_data = ' ( ' + ','.join(row_list) + ')'
            all_row_list.append(one_row_data)

        sql += ' values' + ','.join(all_row_list)
        self.cursor.execute(sql)
        self.clear()
        return

    def update(self, data_dict):
        if self.sql['tables'] == '':
            self.clear()
            raise Exception('缺少table名称')
        update_data_list = []
        for key, value in data_dict.items():
            if type(value) == type('some'):
                update_data_list.append("%s='%s'" % (key, value))
            elif type(value) == type(None):
                update_data_list.append('%s=null' % key)
            elif type(value) == type(datetime.datetime.now()):
                update_data_list.append("%s='%s'" % (key, value))
            elif type(value) == type(datetime.date.today()):
                update_data_list.append("%s='%s'" % (key, value))
            else:
                update_data_list.append('%s=%s' % (key, str(value)))

        sql = 'update %s set ' % self.sql['tables'] + ','.join(update_data_list) + self.get_where()
        self.cursor.execute(sql)
        self.clear()
        return

    def fields(self, fields_str):
        self.sql['fields'] = fields_str
        return self

    def find(self):
        """
        返回结果字典列表
        """
        if self.sql['tables'] == '':
            self.clear()
            raise Exception('缺少table名称')
        sql = 'select '
        if self.sql['fields'] == '':
            sql += '* '
        else:
            sql += self.sql['fields']
        sql += ' from ' + self.sql['tables'] + self.get_where() + self.get_order() + self.get_limit()
        self.cursor.execute(sql)
        self.clear()
        return self.cursor.fetchall()

    def limit(self, count, start = 0):
        self.sql['limit'] = (count, start)
        return self

    def get_limit(self):
        count, start = self.sql['limit']
        if count <= 0:
            return ''
        return ' limit %d, %d ' % (start, count)

    def count(self):
        if self.sql['tables'] == '':
            self.clear()
            raise Exception('缺少table名称')
        sql = 'select '
        sql += ' count(*)  '
        sql += ' from ' + self.sql['tables'] + self.get_where() + self.get_limit()
        self.cursor.execute(sql)
        self.clear()
        return self.cursor.fetchone()['count(*)']

    def order(self, order_dict):
        self.sql['order'] = order_dict
        return self

    def get_order(self):
        if self.sql['order']:
            order_list = []
            for key, value in self.sql['order'].items():
                order = ' asc'
                if value < 0:
                    order = ' desc'
                order_item = key + order
                order_list.append(order_item)

            return ' order by ' + ','.join(order_list) + ' '
        else:
            return ''

    def close(self):
        self.cursor.close()
        self.conn.close()
