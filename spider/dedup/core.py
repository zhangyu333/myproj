#coding=utf-8


"""
文件名:core.py
功能:
    url去重,redis实现
    
代码历史:
    2014-5-5 : 添加add_url函数,该函数只接收一个子符串参数,若参数存在则返回true,成功返回true,异常交外部处理,该函数非线程安全
"""

import threading
import time

import redis

import util

class RedisDB():
    
    def __init__(self, con_str, key):
        self.con_str = con_str
        if not self.con_str.startswith("redis://"):
            self.con_str = "redis://" + self.con_str
        self.key = key
        self.db = self.connect()
        self.lock = threading.Lock()
    
    def connect(self):
        return redis.StrictRedis.from_url(self.con_str)
        
    def search_url(self, url,salt=''):
        result = None
        url = util.canonicalize_url(url)
        self.lock.acquire()
        #result = self.db.sismember(self.key, url)
        try:
            result = self.db.zrank(self.key,salt+url)
        except:
            result = None
        self.lock.release()
        return result
        
    def add_url(self, url, salt=''):
        """
        非线程安全
        """
        url = util.canonicalize_url(url)
        #return self.db.sadd(self.key, url)
        self.lock.acquire()
        try:
            result = self.db.zrank(self.key,salt+url)
        except:
            result = None
        self.lock.release()
        
        if result!=None:
            return False
        else:
            try:
                resp = self.db.zadd(self.key, time.time(), salt+url)
            except:
                resp = False
            return resp
    
    def close(self):
        pass
        
