#coding=utf-8

#############################################################################


'''
文件名：web_config_id.py
功能：基于 帖子id爬虫抓取文件。 

代码历史：
'''
import urllib
import urllib2

import log
import spider
import htmlparser

class Spider(spider.Spider):
    def __init__(self, cmd_args=None, **kwargs):
        spider.Spider.__init__(self, cmd_args=cmd_args, **kwargs)
        
        self.has_topic_id = True
        self.list_url_topic_id = {}
        self.detail_url_topic_id = {}
        
        self.bool_download_detail = True
        self.max_interval = None
        
    def get_list_urls(self):
        '''根据关键词获取列表页url
        '''
        urls_list = []
        keywords = []
        if isinstance(self.keywords_url, list):
            for url in self.keywords_url:
                try:
                    response = urllib2.urlopen(url)
                    kws = response.readlines()
                except Exception,e:
                    kws = ''
                    print "get keyword failed: %s; url: %s"%(e, self.keywords_url)
                finally:
                    keywords += kws
        else:
            try:
                response = urllib2.urlopen(self.keywords_url)
                keywords = response.readlines()
            except Exception,e:
                print "get keyword failed: %s; url: %s"%(e, self.keywords_url)
                return urls_list
        
        for kw in keywords:
            if getattr(self, 'has_topic_id', False):
                topic_id_kw = kw.split('\t')
                topic_id = topic_id_kw[0]
                kw = topic_id_kw[1].strip()
#                kw = ''.join(topic_id_kw[1].split())
            else:
                topic_id = ''
            for i in xrange(self.start_page, self.stop_page):
                if getattr(self, 'encode_name', ''):
                    url = self.search_url%(urllib.urlencode({self.encode_name:kw.strip().decode('utf8').encode(self.encode_encoding)}), self.step_num * i)
                else:
                    url = self.search_url%(kw.strip(), self.step_num * i)
                urls_list.append(url)
                #保存该url及与之对应的topic_id
                self.list_url_topic_id[url] = topic_id
        
        return urls_list
        
    def get_start_urls(self, data=None):
        """
        获取爬虫抓取入口网页地址;
        """
        urls_list = []
        
        if self.bool_download_detail:
            urls_list = self.get_list_urls()
        else:
            urls_list = self.start_urls
        
        return urls_list
    
    def parse(self, response, url=None):
        """
        从远程读取搜索词,构造搜索结果页面url,并返回用户入口url;
        同时，记录结束时间，如果本次从redis中读取的字段中包含结束符的话；
        """
        detail_page_urls = []
        request = url
        url = request.get('url') if isinstance(request, dict) else request
        
        def check_dedup(detail_url, list_url):
            if url:
                try:
                    topic_id = self.list_url_topic_id.get(list_url, '')
                    if self.url_dedup.is_dedup(url, salt=topic_id):
                        return True
                    else:
                        return False
                except Exception, e:
                    print e
            return False
        
        if self.bool_download_detail:
            if response is not None:
                html_body = ''
                try:
                    response.encoding = self.encoding
                    html_body = response.text
                except Exception , e:
                    return (detail_page_urls, None, None)
                
                list_url = response.request.url
                
                data = htmlparser.Parser(html_body, response=response, url=url)
                try:
                    detail_page_urls = self.get_detail_page_urls(data)
                except Exception, e:
                    detail_page_urls = []
                    self.error_info.append((4, "--- get_detail_page_urls --- config_id: %s ; %s"%(self.config_id, e)))
                    log.logger.info("--- get_detail_page_urls --- config_id: %s ; %s"%(self.config_id, e))
                
                if detail_page_urls:
                     detail_page_urls = [url for url in detail_page_urls if not check_dedup(url, list_url)]
                #更新详情页url对应的topic_id
                for detail_url in detail_page_urls:
                    self.detail_url_topic_id[detail_url] = self.list_url_topic_id.get(list_url, '')
        else:
            detail_page_urls = self.get_list_urls()
        
        return (detail_page_urls, None, None)

    def parse_detail_page(self, response=None, url=None):
        '''
        详细页解析;页面下载失败时，保存post_id
        '''
        request = url
        url = request.get('url') if isinstance(request, dict) else request

        if response is not None:
            html_body = ''
            try:
                response.encoding = self.encoding
                html_body = response.text
            except Exception , e:
                return None
            if url is None:
                url = response.reqeust.url
            else:
                response.request.url = url
            
            results = []
            data = htmlparser.Parser(html_body, response=response, url=url)
            try:
                post_infos = self.get_detail_page_info(data)
            except Exception, e:
                post_infos = []
                self.error_info.append((5, "--- get_detail_page_info --- config_id: %s ; %s"%(self.config_id, e)))
                log.logger.info("--- get_detail_page_info --- config_id: %s ; %s"%(self.config_id, e))
            
            if post_infos is None:
                return None
            if not isinstance(post_infos, list):
                post_infos = [post_infos]
            for post in post_infos:
                if self.bool_download_detail:
                    #添加topic_id
                    if getattr(self, 'has_topic_id', False):
                        post.update({'topic_id':self.detail_url_topic_id.get(url, '')})
                    #更新url
                    #post.update({'url':url})
                else:
                    list_url = url
                    if getattr(self, 'has_topic_id', False):
                        post.update({'topic_id':self.list_url_topic_id.get(list_url, '')})
                post_url = post.get('url', '')
                topic_id = post.get('topic_id', '')
                if post_url:
                    url_dedup =  getattr(self, 'url_dedup', None)
                    if url_dedup is not None:
                        try:
                            if not url_dedup.is_dedup(post_url, salt=topic_id):
                                if getattr(self, 'max_interval', None) is not None:
                                    if post['ctime'] > post['gtime'] - self.max_interval:
                                        results.append(post)
                                else:
                                    results.append(post)
                        except:
                            pass
            return results
        else:
            return None

    def get_detail_page_urls(self, data):
        return []
    
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
