#coding=utf-8


"""
文件名:dedup.py
功能:
    查询和增加url是否已经采集
    
代码历史:
    2014-2-25 : 实现代码
    2014-5-5 : 增加单个url外部接口
    2014-07-17：增加salt参数
    
使用示例:
    d = Dedup("127.0.0.1:6379/0","urlset")
    d.is_dedup("www.baidu.com")   return True 存在 False 不存在
    d.append("www.baidu.com")    return int
    
    
    mapping = (("^www.baidu.com$", "127.0.0.1:6379/2", "urlsetTest"),
               ("^test.com$", "127.0.0.1:6379/2", "urlsetTest2"),
               ("^qq.com/[\d]+$", "127.0.0.1:6379/3", "urlsetTestqq")
               )
    d = MappingDedup(mapping, ("127.0.0.1:6379/3","urlsetdefault"))
    print d.is_dedup("www.baidu.com")
    print d.append("www.baidu.com")
    print d.append("www.baidu.com")
    print d.is_dedup("www.baidu.com")
    print d.append("qq.com/3242")
    print d.append("defaultsdfsdf.com")
"""
import re

import core


class Dedup():
    """
    去重查询 添加
    """
    def __init__(self, con_str, key = "urlset", cache = None):
        """
        example : Dedup("127.0.0.1:6379/0")
        """
        self.con_str = con_str
        self.key = key
        self.db = core.RedisDB(con_str, key)
        if cache:
            self.cache = core.RedisDB(cache[0],cache[1])
    
    def is_dedup(self, url, salt=''):
        result = self.db.search_url(url, salt)
        if result is None:
            if hasattr(self,"cache") and self.cache.add_url(url, salt):
                return True
            else:
                return False
        else:
            return True
            
    
    def append(self,url, salt=''):
        result = self.db.add_url(url, salt)
        if result:
            return True
        else:
            return False
    
    def close(self):
        pass

class MappingDedup():
    
    def __init__(self, regex_maps, default, cache=None):
        """
        arg1 : ((regex,con_str,key), (...), ...)
        arg2 : (con_str, key) 无匹配则连接该地址
        """
        if not regex_maps:
            raise Exception("未发现对应关系,如无此对应,请用Dedup类")
        self.cons = []
        for regex_map in regex_maps:
            self.cons.append([re.compile(regex_map[0]), core.RedisDB(regex_map[1], regex_map[2])])
                
        self.default = core.RedisDB(default[0], default[1])
        if cache:
            self.cache = core.RedisDB(cache[0],cache[1])

            
    def get_con_url(self, url):
        for con in self.cons:
            result = con[0].match(url)
            if result:
                if result.groups():
                    return con[1], "".join(result.groups())
                else:
                    return con[1], url
        return self.default,url

        
    def is_dedup(self, url, salt=''):
        con,url = self.get_con_url(url)
        result = con.search_url(url, salt)
        if result is None:
            if hasattr(self,"cache") and self.cache.add_url(url, salt):
                return True
            else:
                return False
        else:
            return True
    
        
    def append(self, url, salt=''):
        con, url = self.get_con_url(url)
        result = con.add_url(url, salt)
        if result:
            return True
        else:
            return False
        
                
    def close(self):
        pass

    
    
def main():
    dedup_mapping = (
        ("^http\://tieba\.baidu\.com/p/(\d+)$", "redis-dupurl-1.istarshine.net.cn:6379/0", "tieba_dedup"),
        ("^http\://weibo\.com/([\s\S]+)$", "redis-dupweibo-1.istarshine.net.cn:6379/0", "sina_dedup"),
        ("^http\://t\.qq\.com/p/t/([\d]+)$", "redis-dupweibo-1.istarshine.net.cn:6379/0", "qq_dedup"),
     )
    dedup_default = ("redis://redis-dupurl-1.istarshine.net.cn:6379/0","dedup")

    url_dedup = MappingDedup(dedup_mapping, dedup_default)

    #print d.get_con_url("www.baidu.com")
    #print d.get_con_url("qq.com/3453534")
    print url_dedup.is_dedup("http://www.jj831.com/education/201505/216551.html")
    print url_dedup.append("http://www.jj831.com/education/201505/216551.html")
    #print d.append("www.baidu.com")
    #print d.is_dedup("www.baidu.com")
    #print d.append("qq.com/3242")
    #print d.append("defaultsdfsdf.com")
    
if __name__ == "__main__":
    main()
