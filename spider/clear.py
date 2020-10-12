
# -*- coding: utf-8 -*-
import spider
import setting
import htmlparser
import redis
from w3lib.html import  remove_tags_with_content
import time
import re
from urlparse import urljoin
import json
import base64
import sys
reload(sys)
sys.setdefaultencoding('utf8')

class MySpider(spider.Spider):
    def __init__(self,
                 proxy_enable=True,
                 proxy_max_num=setting.PROXY_MAX_NUM,
                 timeout=60,
                 cmd_args=None):
        spider.Spider.__init__(self, proxy_enable, proxy_max_num, timeout=timeout, cmd_args=cmd_args)

        # 网站名称
        self.siteName = ""

        # 入口地址列表
        self.start_urls = [None]
        self.encoding = 'utf-8'
        self.site_domain = ''
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36",
            # "Cookie":"UM_distinctid=16f6401a8b11a9-00a5a1880237ff-5146291a-1fa400-16f6401a8b268c; _ma_tk=auli5o1hponaq6dl0qhwwl91dgqd0ciw; zycna=ZAT6lRWmIZoBAXgk/FYkZTUJ; Hm_lvt_8b4d7aee0143637104971c209767657f=1577930690,1577932630; JSESSIONID=CD47029CAD445CEDBB86F7B0E08CB3E7; _ma_starttm=1577936794767; _ma_is_new_u=0; Hm_lpvt_8b4d7aee0143637104971c209767657f=1577937545",
        }
        self.request_headers = {'headers': self.headers}
        self.config_info = "{'level':'1','type':'1'}"
        try:
            self.url_db = redis.StrictRedis.from_url('redis://39.108.182.112:16380/1')
        except:
            self.url_db = None
        self.limits = 2
        self.timeout =20
        # self.proxy_url = "http://vip22.xiguadaili.com/ip/?tid=556531119318925&num=210&category=2&delay=5&format=json"

        self.zjr_inter_url_list = 'lunxun_internet_media_test'

        # self.data_db = "kafka://172.18.224.209:9092/po-wechat-overview"
        # self.data_db = "kafka://172.18.224.182:9092/po-wechat-overview"
        # self.data_db = "rocketmq://120.24.236.85:16380/15/zy"


    def get_start_urls(self, data=None):
        filenames = [
            'zy_bbtnewscomcn_detail_test.py',
            'zy_cnrcn_detail_test.py',
            'zy_cricn_detail_test.py',
            'zy_pengpaisearchinterface_detail_test.py',
            'zy_wwwoeeeecom_detail_test.py',
            'zy_wwwthepapercn_user_detail_test.py',
            'zy_wwwthepengpainewscn_detail_test.py',
            'zy_xinhuanetcom_detail_test.py',
            'zy_wwwthepapercn_user_test.py',
            ]
        for filename in filenames:
            self.url_db.lrem(self.zjr_inter_url_list,0,filename)
        return None
    def parse(self, response, url):

        return [None,None,None]

    def parse_detail_page(self, response=None, url=None):
        return []
#

if __name__ == '__main__':
    spider = MySpider()
    spider.proxy_enable = True
    spider.init_dedup()
    spider.init_downloader()
    spider.get_start_urls()