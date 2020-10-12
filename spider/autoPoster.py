#!/usr/bin/env python
#coding=utf-8

#############################################################################


'''
文件名：autoPoster.py
功能：自动发帖类。 

代码历史：
2015-02-09：庞  威  代码创建
'''
import Queue

import redis
try:
    import ujson as json
except ImportError:
    import json

import log
import spider
import setting


class AutoPoster(spider.Spider):
    def __init__(self, cmd_args=None, **kwargs):
        spider.Spider.__init__(self, cmd_args=cmd_args, **kwargs)
        
        self.siteName = ''
        self.start_urls = [None]
        
        #所要发贴信息存放db
        self.conn = redis.StrictRedis.from_url('redis://192.168.123.1/15')
        self.key_result = 'auto_posts_results'
        #发贴信息存放key值
        self.key_name = None
        #每次发贴数目
        self.limits = 1
        
        self.all_posts = Queue.Queue()
        self.adsl_id = getattr(setting, 'ADSL_ID', -1)
        self.spider_id = getattr(setting, 'SPIDER_ID', -1)
    
    def get_start_urls(self, data=None):
        """
        获取爬虫抓取入口网页地址;
        """
        return self.start_urls
    
    def parse(self, response):
        """
        从远程读取搜索词,构造搜索结果页面url,并返回用户入口url;
        同时，记录结束时间，如果本次从redis中读取的字段中包含结束符的话；
        """
        detail_page_urls = []
        
        posts = self.get_posts_from_db()
        for post in posts:
            #self.download('www.baidu.com') return None for url not start with http
            detail_page_urls.append('www.baidu.com')
            self.all_posts.put(post)
            print "--post: ", post
        
        return (detail_page_urls, None, None)
    
    def get_posts_from_db(self):
        '''
        从数据库中读取发贴信息
        '''
        posts = []
        posts_user = {}
        try:
            pipe = self.conn.pipeline()
            if self.key_name is not None:
                for i in xrange(self.limits):
                   pipe.rpop(self.key_name)
            all_posts = pipe.execute()
            #posts = [item for item in posts if item is not None]
            #同一个用户不能同时发帖
            for item in all_posts:
                if item is None:
                    continue
                post = json.loads(item)
                username = post.get('username')
                #包含指定用户
                if username is not None:
                    #该指定用户已有发帖任务
                    if username in posts_user:
                        try:
                            #将同一用户的其他帖子放回库中供下次发送
                            self.conn.lpush(item)
                        except:
                            posts.append(post)
                    else:
                        posts.append(post)
                        #保存发帖username
                        posts_user[username] = 1
                else:
                    posts.append(post)
        except Exception, e:
            log.logger.error("--0-- get_posts_from_db() failed: %s"%e)
            posts = []
        print "--total post: ", len(posts)
        return posts
    
    
if __name__ == "__main__":
    spider = AutoPoster()
    spider.proxy_enable = False
    spider.init_dedup()
    spider.init_downloader()
    
    spider.parse_list_page_finish = True
    
    
# ------------ get_start_urls() ----------
#     urls = spider.get_start_urls()
#     for url in urls:
#         print url

# ------------ parse() ----------
#     urls, fun, next_url = spider.parse(None)
#     for url in urls:
#         print url

    spider.parse_detail_page(None, None)
    