#filename:db.py
#encoding=utf8
'''
用于数据库相关的一些方法
delete
update
find
支持连贯操作
    

'''

import ConfigParser
import log
import util
import urlparse
from abc import ABCMeta, abstractmethod


class DbOpt():
    '''抽象框架'''
    __metaclass__ = ABCMeta

    def __init__(self, setting_dict):
        self.setting_dict = setting_dict
     
    @abstractmethod
    def delete(self):
        return self

    @abstractmethod
    def where(self, condition):
        return self
    
    @abstractmethod
    def table(self, table_str):
        return self
    
    @abstractmethod
    def add(self, data_dicts):
        pass
    
    @abstractmethod
    def update(self, data_dict):
        pass
    
    @abstractmethod
    def find(self):
        pass
    
    @abstractmethod
    def limit(self, count, start=0):
        pass
    
    @abstractmethod
    def count(self):
        pass
    
    @abstractmethod
    def order(self, order_dict):
        pass
    
    @abstractmethod
    def close(self):
        pass


class DB():
    '''
    当例连接的方法，支持mysql和mongo等，无需用sql或者js，直接CRUD操作
    '''
    def __init__(self):
        pass
    
    def create(self, conn_str):
        
        if conn_str is None:
            raise Exception("参数为空")
         
        self.conn_str = conn_str
        
        import re

        if re.match("(\w+://)", conn_str) is None:
            cfg = ConfigParser.ConfigParser()
            try:
                cfg.read(util.get_current_file_path()  + "/db.conf")
                self.conn_str = cfg.get("connections", conn_str)
            except:
                raise Exception("配置文件db.conf中没有相应项，或者错误")
            
        db_setting_uri = urlparse.urlparse(self.conn_str)

        setting_dict = {}
        setting_dict["type"] = db_setting_uri.scheme
        setting_dict["host"] = db_setting_uri.hostname
        setting_dict["port"] = db_setting_uri.port
        setting_dict["username"] = db_setting_uri.username
        setting_dict["password"] = db_setting_uri.password
        setting_dict["db"] = db_setting_uri.path.strip('/')
        setting_dict["params"] = db_setting_uri.query
        
        if setting_dict["type"] == "mysql":
            import db_mysql
            self.db_opt = db_mysql.MySQLOpt(setting_dict)
            
        elif setting_dict["type"] == "mongo":
            import db_mongo
            self.db_opt = db_mongo.MongoOpt(db_setting_uri)
        else:
            raise Exception("未知的协议：%s"%setting_dict["type"])
        
        return self.db_opt
        

if __name__ == "__main__":
    db = DB().create("mysql://root:130809@192.168.100.12:3306/m_1688")
#     for i in range(100):
#         data = {}
#         data["id"] = i 
#         data["username"] = "kronus"
#         db.table("users").add(data)
    data = {'title':'hello', 'price':1111, 'ghzl':'123',
                           'kssl':'kssl',
                           'ljcs':'ljcs',
                           'fhd':'fhd',
                           'contactor':'pw',
                           'contact':'13811837909',
                           'company_id':'123456789'}
    result = db.table("woman_dress").add(data)
    print result
    db.close()
    

    
    