#coding=utf-8

#############################################################################


'''
文件名：web_config_id.py
功能：基于 帖子id爬虫抓取文件。 

代码历史：
'''
import log
import datetime
import spider
import htmlparser

class Spider(spider.Spider):
    def __init__(self, cmd_args=None, **kwargs):
        spider.Spider.__init__(self, cmd_args=cmd_args, **kwargs)
        
        
    def get_start_urls(self, data=None):
        """
        获取爬虫抓取入口网页地址;
        """
        return self.start_urls
    
    def parse(self, response, url=None):
        """
        从远程读取搜索词,构造搜索结果页面url,并返回用户入口url;
        同时，记录结束时间，如果本次从redis中读取的字段中包含结束符的话；
        """
        detail_page_urls = []
        request = url
        url = request.get('url') if isinstance(request, dict) else request
        if response is not None:
            try:
                response.encoding = self.encoding
                unicode_html_body = response.text
            except Exception as e:
                return (detail_page_urls, None, None)
            
            data = htmlparser.Parser(unicode_html_body, response=response, url=url)
        else:
            data = None

        detail_page_urls = self.get_detail_page_urls(data)

        return (detail_page_urls, None, None)
    
    
    def parse_detail_page(self, response=None, url=None):
        '''
        详细页解析;页面下载失败时，保存post_id
        '''
        if response is not None:
            request = url
            url = request.get('url') if isinstance(request, dict) else request
            try:
                response.encoding = self.encoding
                unicode_html_body = response.text
            except Exception as e:
                return None
            if url is None:
                url = response.request.url
            
            results = []
            data = htmlparser.Parser(unicode_html_body, response=response, url=url)
            
            post_infos = self.get_detail_page_info(data)

            if post_infos is None:
                return None
            
            if not isinstance(post_infos, list):
                post_infos = [post_infos]
            
            new_posts = []
            for post in post_infos:
                if 'url' not in post and url is not None:
                    post['url'] = url
                
                if self.max_interval is not None:
                    if isinstance(self.max_interval, int):
                        self.max_interval = datetime.timedelta(self.max_interval)
                    if post['ctime'] >= post['gtime'] - self.max_interval:
                        new_posts.append(post)
                    else:
                        if self.urldedup is not None:
                            try:
                                self.urldedup.append(post['url'])
                            except:
                                pass
                else:
                    new_posts.append(post)
            
            return new_posts
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
