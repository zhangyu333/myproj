#encoding=utf8

#
# 文件名：data_buffer.py
# 功能：实现基于redis、mysql等的FIFO数据队列
#
# 接口调用范例：
#
#    data_buffer = BufferFactory().create("redis://192.168.2.122/0/test")
#    data_buffer.push({"dafasdfasdf":12341324})
#    print data_buffer.pop()
#
# 代码历史：

# 2014-06-20：增加pushall方法
# 2015-04-03：push和pop支持json，默认为pickle
# 2016-08-16：redis支持用户名和密码
# 2016-08-17： pop支持FILO
# 2017-07-26：pop增加unicode转utf8，以及json反序列化ctime和gtime的unix时间戳转换
# 2017-09-01：push json格式增加ensure_ascii=False，防止序列化错误事情
# 2017-10-12：增加log模块，用于记录异常信息

import redis
from urllib2 import urlparse
import cPickle as pickle
try:
    import ujson as json
except ImportError:
    import json
import time
import datetime
import log
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

class Buffer:

    def __init__(self, uri):
        self.uri = uri

    def push(self, data):
        pass

    def pop(self):
        return None

    def pushall(self, data_list):
        pass


class RedisBuffer(Buffer):

    def __init__(self, uri):
        self.host = uri.netloc.split(':')[0]
        self.port = uri.netloc.split(':')[-1]
        self.password = uri.password
        self.username = uri.username
        self.db, self.key_name = filter(lambda x: x != '', uri.path.split('/'))[:2]
        self.conn = redis.StrictRedis(host=self.host, port=self.port, db=self.db, password=self.password)
    def push(self, data, dest_json = False):
        if dest_json:
            push_data = json.dumps(data,ensure_ascii=False)
        else:
            push_data = pickle.dumps(data)
        try:
            self.conn.lpush(self.key_name, push_data)
        except Exception,e:
            log.logger.exception( "redis push exception:%s, delay 0.1s retry, %s"%(e, repr(push_data)))
            time.sleep(0.1)
            try:
                self.conn.lpush(self.key_name, push_data)
            except Exception, e:
                log.logger.exception("conn.lpush(self.key_name, push_data): %s"%e)
            

    def pushall(self, data_list, dest_json = False):
        pipe = self.conn.pipeline()
        for data in data_list:
            try:
                if dest_json:
                    dest_data = json.dumps(data)
                else:
                    dest_data = pickle.dumps(data)
                pipe.lpush(self.key_name, dest_data)
            except Exception, e:
                log.logger.exception("json.dumps:%s"%e)


        try:
            pipe.execute()
        except Exception, e:
            log.logger.exception("pushall pipe execute exception: %s"%e)
            
            time.sleep(2.0)
            try:
                pipe.execute()
            except Exception, e:
                log.logger.exception("pushall pipe execute exception2: %s"%e)

    def pop(self, src_json=False, new_first=True):
        """
        所有编码都为utf8，如果为unicode，会自动转成utf8
        """
        src_data = ""
        try:
            if new_first:
                src_data = self.conn.lpop(self.key_name)
            else:
                src_data = self.conn.rpop(self.key_name)
        except Exception, e:
            log.logger.exception( "buffer redis pop exception: %s, src_data=%s"%(e,repr(src_data)))
            return None

        if not src_data:
            return None
        
                        
        if src_json:
            try:
                data =  json.loads(src_data)
                #转成utf8编码
                try:
                    for k,v in data.iteritems():
                        if isinstance(v, unicode):
                            data[k] = v.encode("utf-8")
                except Exception, e:
                    log.logger.exception( "pop decode utf8:%s, %s"%(e, repr(data)))
                
                ctime = data.get("ctime", None)
                if ctime:
                    if isinstance(ctime, (int,float)):
                        #utc时间
                        data["ctime"] = datetime.datetime.utcfromtimestamp(ctime)
                gtime = data.get("gtime", None)
                if gtime:
                    if isinstance(gtime, (int,float)):
                        data["gtime"] = datetime.datetime.utcfromtimestamp(gtime)
                        
                return data        
            except Exception, e:
                log.logger.exception( "buffer pop json load exception: %s,%s"%(e, repr(src_data)))
                return None
        else:
            try:
                data = pickle.loads(src_data)
                #转成utf8编码
                try:
                    for k,v in data.iteritems():
                        if isinstance(v, unicode):
                            data[k] = v.encode("utf-8", errors="ignore")
                except Exception, e:
                    log.logger.exception( "pop decode utf8:%s, %s"%(e, repr(data)) )
                    
                return data
            
            except Exception, e:
                log.logger.exception( "buffer pop picke exception: %s, src_data=%s"%(e, repr(src_data)))
                return None


class BufferFactory:

    def create(self, url):
        uri = urlparse.urlparse(url)
        if uri.scheme not in ('redis', 'mysql', 'mongodb'):
            raise Exception, '\xe7\xb1\xbb\xe5\x9e\x8b\xe5\xbc\x82\xe5\xb8\xb8\xef\xbc\x8c \xe5\xbf\x85\xe9\xa1\xbb\xe6\x98\xafredis, mysql\xe6\x88\x96\xe8\x80\x85mongodb'
        if uri.scheme == 'redis':
            return RedisBuffer(uri)


if __name__ == '__main__':
    data_buffer = BufferFactory().create('redis://192.168.2.122/0/test')
    print data_buffer.pop()
