#coding=utf-8

#############################################################################


'''
文件名：web_config_id.py
功能：基于 帖子id爬虫抓取文件。 

代码历史：

'''
import re
import time
import threading
import datetime

import redis

import log
import spider
import setting
import htmlparser
from dedup import dedup

class Spider(spider.Spider):
    def __init__(self, cmd_args=None, **kwargs):
        spider.Spider.__init__(self, cmd_args=cmd_args, **kwargs)
        
        #保存页面不存在时post_id
        self.page_404_ids = set()
        #保存下载失败时post_id
        self.page_download_failed_ids = set()
        #本次成功抓取最大id
        self.largest_successed_post_id = 0
        #本次抓取开始前最大成功抓取帖子id
        self.last_successed_post_id = 0
        #阀值 控制采集太快导致的漏采
        self.interval_404 = 500
        #每次最少新url数目，避免全部url为重试url
        self.least_new_url_limits = 0
        #每次加载新url：包括重试url及新生成url
        self.limits = 30
        
        
    def before_stoped(self, **kwargs):
        '''
        根据成功下载的最大post_id判断self.page_404_ids中帖子是不存在贴，还是未发表贴；
        '''
        if self.post_id_db is not None:
            pipe = self.post_id_db.pipeline()
            #下载失败帖子全部放入重试库
            for post_id in self.page_download_failed_ids:
                pipe.lpush(self.key_retry_post_ids, post_id)
                print " ---- %s ---- download failed post_id: %s"%(self.siteName, post_id)
            #pipe.execute()
            #
            for post_id in self.page_404_ids:
                #未发表帖子
                if long(post_id) > long(self.last_successed_post_id) - self.interval_404:
                    pipe.lpush(self.key_retry_post_ids, post_id)
                    print " ---- %s --- page has not been posted ---- :%s "%(self.siteName, post_id)
                #post_id有效，该贴被封
                else:
#                    pipe.zadd(self.key_404_post_ids, 0, post_id)
                    print " ---- %s --- *** page_not_exist *** : %s"%(self.siteName, post_id)
            try:
                pipe.execute()
            except Exception, e:
                print e
                
            #更新成功下载帖子最大id
            if long(self.largest_successed_post_id) > long(self.last_successed_post_id):
                for i in range(3):
                    try:
                        pipe.get(self.key_last_largest_post_id)
                        last_largest_post_id = long(pipe.execute()[0])
                        if last_largest_post_id < self.largest_successed_post_id:
                            pipe.watch(self.key_last_largest_post_id)
                            pipe.multi()
                            pipe.set(self.key_last_largest_post_id, self.largest_successed_post_id)
                            pipe.execute()
                        break
                    except redis.exceptions.WatchError:
                        pass
                    except Exception as e:
                        log.logger.exception(e)
                        
           
    def get_start_urls(self, data=None):
        """
        获取爬虫抓取入口网页地址;
        """
        return self.start_urls
    
    def parse(self, response, url=None):
        """
        首先从key_retry_post_ids读取post_id，构造帖子url;
        然后，在根据key_largest_post_id保存的post_id，向后生成url
        两者相加生成的url不超过limits设定的数目
        """
        detail_page_urls = []
        request = url
        url = request.get('url') if isinstance(request, dict) else request
        if self.post_id_db is not None:
            #
            def check_dedup(url):
                try:
                    if self.url_dedup.is_dedup(url):
                        return True
                except Exception, e:
                    print e
                return False
            
            try:
                self.last_successed_post_id = self.post_id_db.get(self.key_last_largest_post_id)
                self.last_successed_post_id = long(self.last_successed_post_id)
            except Exception, e:
                self.last_successed_post_id = None
            if self.last_successed_post_id is None:
                self.last_successed_post_id = 0
            
            pipe = self.post_id_db.pipeline()
            for i in xrange(self.limits - self.least_new_url_limits):
                pipe.rpop(self.key_retry_post_ids)
            try:
                retry_post_ids = pipe.execute()
                retry_post_ids = [post_id for post_id in retry_post_ids if post_id is not None]
                new_post_ids_num = self.limits - len(retry_post_ids)
            except:
                retry_post_ids = []
                new_post_ids_num = 0
            print " - 1 - new_post_ids_num :", new_post_ids_num
            #构造新的帖子id
            if new_post_ids_num > 0 and self.post_id_db.exists(self.key_largest_post_id):
                largest_post_id = self.post_id_db.incrby(self.key_largest_post_id, new_post_ids_num)
                largest_post_id = long(largest_post_id)
                new_url_ids = [largest_post_id-i for i in xrange(new_post_ids_num)]
                retry_post_ids += new_url_ids
            
            if retry_post_ids:
                #根究post_id构造post_url
                detail_page_urls = [self.post_url%(post_id) for post_id in retry_post_ids]
                #url去重
                #detail_page_urls = [url for url in detail_page_urls if not check_dedup(url)]
        
        return (detail_page_urls, None, None)


    def parse_detail_page(self, response=None, url=None):
        '''
        详细页解析;页面下载失败时，保存post_id
        '''
        request = url
        url = request.get('url') if isinstance(request, dict) else request
        if response is not None:
            m = self.re_post_id.search(url)
            if m:
                post_id = long(m.group(1))
            else:
                print "can not search self.re_post_id in url : %s"%url
                return None
            
            unicode_html_body = u''
            try:
                response.encoding = self.encoding
                unicode_html_body = response.text
            except Exception , e:
                self.page_download_failed_ids.add(post_id)
                print "Exception : %s;  url: %s"%(e, url)
                return None
            
            #下载页面内容失败
            if not unicode_html_body:
                self.page_download_failed_ids.add(post_id)
                return None
            #判断本帖是否存在
            m  = self.re_page_404.search(unicode_html_body)
            if m:
                self.page_404_ids.add(post_id)
                #print "----  404  ---; post_id: %s"%(post_id)
                return {}
            
            data = htmlparser.Parser(unicode_html_body, response=response, url=url)
             
            try:
                result = self.get_detail_page_info(data)
            except Exception, e:
                result = None
                log.logger.info("--- get_detail_page_info ---config_id: %s ; %s"%(self.config_id, e))
                self.error_info.append((5, "--- get_detail_page_info --- config_id: %s ; %s"%(self.config_id, e)))
            
            if result is None:
                self.page_404_ids.add(post_id)
                #print "----  404  ---; post_id: %s"%(post_id)
                return {}
            #全部字段解析失败
            if not (result.get('title','') or result.get('content','') or result.get('author','')):
                 self.page_download_failed_ids.add(post_id)
                 print " ------------------------------ 222 ------- response is None -----"
                 return None
            else:
                if long(self.largest_successed_post_id) < long(post_id):
                    self.largest_successed_post_id = post_id
            return result
        else:
            if url is not None:
                m = self.re_post_id.search(url)
                if m:
                    post_id = long(m.group(1))
                    self.page_download_failed_ids.add(post_id)
                else:
                    print "can not search self.re_post_id in url : %s"%url
            return None
    
    def get_detail_page_info(self, data):
        return {}

if __name__ == "__main__":
    import requests
#    url = "http://192.168.2.116/athena1/trunk/web/task/task.php/Data/index"
    url = "http://192.168.110.6/task.php/Data/index"
    spider = MySpider()
    spider.proxy_enable = False
    spider.init_dedup()
    spider.init_downloader()
    
    spider.parse_list_page_finish = True
    
# ------------ is_dedup() ----------
#    url = 'http://tieba.baidu.com/p/3141988823'
#     url = '3141986823'
#     if spider.url_dedup.is_dedup(url):
#         print "this url exist:"
#     else:
#         print "this url not exist:"
#     
# ------------ get_start_urls() ----------
#     urls = spider.get_start_urls()
#     for url in urls:
#         print url

# ------------ parse() ----------
#     urls, fun, next_url = spider.parse()
#     for url in urls:
#         print url

# ------------ parse_detail_page() ----------
    url = 'http://bbs.hsw.cn/read-htm-tid-6747328.html'
    resp = spider.download(url)
#    print resp.text
    res = spider.parse_detail_page(resp, url)
    for k, v in res.iteritems():
        print k, v

# ------------ parse() ----------
