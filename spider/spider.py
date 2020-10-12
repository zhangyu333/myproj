#!/usr/bin/env python
# coding:utf-8

#############################################################################


'''
文件名：spider.py
功能：该模块实现爬出抓取的基本功能；负责初始化爬虫参数值；

代码历史：

'''
import gevent.lock
import gevent.event

# from gevent import monkey
# monkey.patch_all()

import json
import time
import copy
import urllib
import urllib2
import traceback
import datetime
import pprint
import urlparse
import base64
import zlib
from collections import defaultdict, deque

import log
import util
import setting
import downloader
from dedup import dedup

import myreadability

INIT_PROXY_FAILED = 0
INVALID_URL = 1
DOWNLOAD_FAILED = 1
PARSE_LIST_FAILED = 2
PARSE_DETAIL_FAILED = 3


class Spider(object):
    """docstring for Spider"""

    def __init__(self, proxy_enable=setting.PROXY_ENABLE,
                 proxy_max_num=setting.PROXY_MAX_NUM,
                 timeout=setting.HTTP_TIMEOUT,
                 cmd_args=None, **kwargs):
        super(Spider, self).__init__()
        self.kwargs = kwargs
        # 是否使用代理
        self.proxy_enable = proxy_enable
        cmd_proxy = getattr(cmd_args, 'PROXY_ENABLE', '')
        if cmd_proxy != '':
            self.proxy_enable = cmd_proxy
        # 每个代理最多连续重复使用次数
        self.proxy_max_num = getattr(cmd_args, 'PROXY_MAX_NUM', None) or proxy_max_num
        #
        self.timeout = getattr(cmd_args, 'HTTP_TIMEOUT', None) or timeout
        # 本次采集开始时间
        self.start_time = datetime.datetime.utcnow()
        # 本次采集结束时间
        self.end_time = None
        # 本次采集到的数据总数
        self.total_data_num = 0
        # 本次采集去重后得到的新数据条数
        self.new_data_num = 0
        # 解析成功的数据数目
        self.parsed_success_num = 0
        # 解析失败的数据数目
        self.parsed_failed_num = 0
        # 下载失败的数据数目
        self.download_failed_num = 0
        #
        self.lock = gevent.lock.RLock()
        self.parse_list_page_finish = False
        self.job_event = gevent.event.Event()
        # 错误信息列表；每一项格式为(error_code, error_info)
        # error_code: 0： 获取代理失败； 1：下载失败； 2：解析数据失败
        self.error_info = []
        self.failed_info = defaultdict(list)
        self.parse_failed = {}
        self.worker_id = ""
        self.config_id = ""
        self.config_name = ""
        self.job_id = ""
        self.last_crawl_time = None
        self.spider_id = ""
        # 采集入口url
        self.start_urls = []
        self.max_interval = datetime.timedelta(days=20)
        # 类别码，01=新闻,02=论坛,03=博客,0401=新浪微博,0402=腾讯微博
        self.info_flag = '01'
        # 创建一个 deque 来存储列表页和详情页的对应关系，不用list，是为了保证线程安全
        self.detail_url_channel_url_deque = deque()
        self.siteName = ""
        # 代理文件地址
        self.proxy_url = ""
        # 去重库地址
        self.dedup_uri = ""
        self.dedup_key = ""
        #
        self.detail_page_queue = None
        # 抓取数据入库地址
        self.data_db = ""
        # 日志信息入库地址
        self.log_db = ""

        # duanyifei add begin on 2016-05-27
        # 数据总数不为0标志
        self.has_total_data = 0
        # 详情页解析数据记录
        self.detail_page_record_list = []
        # 函数执行异常记录
        self.exceptions_info_list = []
        # 类型检查失败信息记录
        self.field_type_failed_record = []
        # url格式错误信息记录
        self.url_format_error_record = defaultdict(list)
        # 字段类型预定义
        self.field_type_dic = self.get_field_type()

        # 配置监测开关
        self.config_monitor = setting.CONFIG_MONITOR
        #请求间隔
        self.request_interval = 0
        self.request_headers = {}
        # 调试模式标志位
        self.debug = getattr(cmd_args, 'debug', False)
        # 配置文件相关信息 从任务分发处获取
        self._conf_info = {}

    def before_stoped(self, **kwargs):
        """可覆盖接口 爬虫全部结束前调用  默认传入 log_data参数(爬虫运行日志)"""
        return

    def before_save_data(self, data, handle=True):
        """钩子 采集到的数据送入入库队列之前会经过这里
        handle:
            True 数据已经被处理过
            False 原生数据 即 parse_detail_page 返回的
        """
        return data
    @property
    def monitor_on(self):
        """判断是否开启配置监测"""
        #
        if self.config_monitor:
            # 仅 spider 类型的爬虫开启监测
            if setting.SPIDER_TYPE in ["spider"]:
                return 1
        return 0

    def init_setting(self):
        '''
        初始化 去重 入库 代理
        '''
        data_db = self._conf_info.get("data_db", "")
        dedup_info = self._conf_info.get("dedup", "")
        proxy = self._conf_info.get("proxy", "")
        data_type = self._conf_info.get("data_type", "")
        proxy_url = self._conf_info.get("proxy_url", "")
        log_db = self._conf_info.get("log_db", "")

        # 入库地址
        if not self.data_db:
            self.data_db = data_db.strip()
            if not self.data_db:
                self.data_db = setting.SPIDER_DATA_DB

        # 去重地址
        dedup_key = ''
        dedup_uri = ''
        if dedup_info:
            dedup_info_parse = urlparse.urlparse(dedup_info)
            dedup_key = dedup_info_parse.path.split("/")[-1]
            dedup_uri = "%s/%s" % (dedup_info_parse.netloc, dedup_info_parse.path.split("/")[1])
        if not self.dedup_key and self.dedup_key is not None:
            self.dedup_key = dedup_key
            if not self.dedup_key:
                self.dedup_key = setting.DEDUP_KEY
        if not self.dedup_uri and self.dedup_uri is not None:
            self.dedup_uri = dedup_uri
            if not self.dedup_uri:
                self.dedup_uri = setting.DEDUP_URI

        # 代理
        if self.proxy_enable == '':
            if proxy:
                self.proxy_enable = True if int(proxy) == 1 else False
            else:
                self.proxy_enable = setting.PROXY_ENABLE
                if not isinstance(self.proxy_enable, bool):
                    self.proxy_enable = False

        # proxy_url
        if not self.proxy_url:
            self.proxy_url = proxy_url
            if not self.proxy_url:
                self.proxy_url = setting.PROXY_URL

        # log_db
        if not self.log_db:
            self.log_db = log_db
            if not self.log_db:
                self.log_db = setting.SPIDER_LOG_DB
        return

    def init_downloader(self):
        """
        初始化downloader
        """
        self.downloader = downloader.Downloader(self.proxy_enable,
                                                self.proxy_max_num,
                                                proxy_url=self.proxy_url,
                                                timeout=self.timeout)

    def init_dedup(self):
        """
        初始化去重库
        """
        if self.dedup_uri and self.dedup_key:
            try:
                self.urldedup = dedup.Dedup(self.dedup_uri, self.dedup_key)
            except Exception as e:
                log.logger.error("init dedup failed: %s; dedup: %s" % (e, self.dedup_uri))
        else:
            self.urldedup = None

    def increase_total_data_num(self):
        """
        设置采集总数
        """
        self.lock.acquire()
        self.total_data_num += 1
        self.lock.release()

    def increase_new_data_num(self, number=1):
        """
        设置新数据总数
        """
        self.lock.acquire()
        self.new_data_num += number
        self.lock.release()

    def increase_parsed_success_num(self):
        """
        解析成功数目加1
        """
        self.lock.acquire()
        self.parsed_success_num += 1
        self.lock.release()

    def increase_parsed_failed_num(self):
        """
        解析失败数目加1
        """
        self.lock.acquire()
        self.parsed_failed_num += 1
        self.lock.release()

    def increase_download_failed_num(self):
        """
        下载失败数目加1
        """
        self.lock.acquire()
        self.download_failed_num += 1
        self.lock.release()

    def set(self):
        """
        设置列表页解析已完成标志位为True
        """
        self.parse_list_page_finish = True

    def is_set(self):
        """
        列表页解析工作是否已结束
        """
        return self.parse_list_page_finish

    def set_config_id(self, config_id):
        self.config_id = config_id

    def set_worker_id(self, worker_id):
        self.worker_id = worker_id

    def set_job_id(self, job_id):
        self.job_id = job_id

    def set_data_queue(self, queue):
        self.crawler_data_queue = queue

    def set_detail_page_queue(self, queue):
        self.detail_page_queue = queue

    def set_spider_id(self, spider_id):
        self.spider_id = spider_id

    def set_config_name(self, config_name):
        self.config_name = config_name

    def get_start_urls(self, data=None):
        '''
        返回start_urls
        '''
        return self.start_urls

    def send_update_cmd(self, data=None):
        """
        抓取结束后更新数据库
        """
        pass

    def send_cmd_to(self, url, post_data):
        """
                抓取结束后更新数据库
        """
        if not url:
            return []
        try:
            j_data = json.dumps(post_data)
        except Exception as e:
            j_data = '{}'
            log.logger.error("post_data is %s; exception: %s" % (str(post_data), e))
        p_data = {"data": j_data}
        e_data = urllib.urlencode(p_data)

        try:
            response = urllib2.urlopen(url, e_data, timeout=15).read()
        except Exception as e:
            log.logger.info("send_cmd_to(): url:%s, Exception:%s" % (url, e))
            return []
        if not response:
            return []
        try:
            data = json.loads(response)
        except Exception as e:
            log.logger.info("send_cmd_to.json.load(): exception: %s; url:%s" % (e, url))
            return []
        return data

    def request_callback(self, request):
        '''
         需要处理特殊的request，例如header
        '''
        return request

    def download(self, request, func_name=None, **kwargs):
        '''
        '''
        if self.request_interval:
            time.sleep(self.request_interval)
        kwargs.update(self.request_headers)
        response = None

        url = request.get('url') if isinstance(request, dict) else request
        if isinstance(url, basestring):
            newurl_lower = url.lower().strip()
            if (newurl_lower.startswith('http://') or
                    newurl_lower.startswith('https://') or
                    newurl_lower.startswith('ftp://')):
                response = self.downloader.download(request, **kwargs)
            else:
                log.logger.info("-- config_id:%s ; url not start with http/https/ftp: %s" % (self.config_id, url))
                self.url_format_error_record[func_name].append(url)
                self.url_format_error_record[func_name] = self.url_format_error_record[func_name][:100]
        else:
            log.logger.error("-- config_id:%s ; url not instance of basestring or dict: %s" % (self.config_id, url))
        return response

    def check_url_list(self, url_list, url):
        """
        判断参数url_list是否为空，如果为空，记为列表页解析错误;
        参数url表示当前页地址；url_list是从url网页中解析出来的结果；
        """
        if not url_list:
            pass
            # self.error_info.append((PARSE_LIST_FAILED, 'PARSE_LIST_FAILED: no item in page:%s'%url))

    def spider_finished(self):
        """
        判断本次抓取所有工作是否结束；如果是，发送本次爬取结果统计信息；
        """
        if self.parse_list_page_finish:
            self.lock.acquire()
            if self.new_data_num == (self.parsed_success_num +
                                         self.parsed_failed_num +
                                         self.download_failed_num):
                #
                if self.new_data_num > self.download_failed_num:
                    for key, value in self.parse_failed.iteritems():
                        if value:
                            self.error_info.append(
                                (PARSE_DETAIL_FAILED, "PARSE_DETAIL_FAILED; parse %s failed; " % key))
                            for err in self.failed_info[key]:
                                self.error_info.append((PARSE_DETAIL_FAILED, err))

                # duanyifei begin 2016-5-23
                error_reason = defaultdict(dict)
                # 指定监控或者debug模式下 收集配置运行信息
                if self.monitor_on or self.debug:

                    # 字段解析失败记录
                    for k, v in self.failed_info.iteritems():
                        error_reason['field_parse_error'].update(
                            {k: "{}/{}/{}".format(len(v), self.new_data_num, self.total_data_num)})

                    # 异常处理
                    if self.exceptions_info_list:
                        exc_urls = defaultdict(list)
                        exc_format = {}
                        for exc_dic in self.exceptions_info_list:
                            e_name = exc_dic['e_name']
                            exc_urls[e_name].append(exc_dic['url'])
                            format_exc = exc_dic['detail']
                            exc_format[e_name] = format_exc

                        for e_name, format_exc in exc_format.items():
                            error_reason['exceptions'].update({
                                e_name: {
                                    'urls': exc_urls.get(e_name, [])[:100],
                                    'exc_info': format_exc,
                                }
                            })

                    # 字段类型检查失败
                    if self.field_type_failed_record:
                        error_reason['field_type_error']["data"] = self.field_type_failed_record[:100]

                    # url格式错误处理
                    if self.url_format_error_record:
                        error_reason['url_format_error'].update(self.url_format_error_record)
                        # duanyifei end 2016-5-23
                response = {'start_time': time.mktime(self.start_time.timetuple()),
                            'end_time': time.mktime(datetime.datetime.utcnow().timetuple()),
                            'total_data_num': self.total_data_num,
                            'new_count': self.new_data_num,
                            'parse_success_num': self.parsed_success_num,
                            'parse_failed_num': self.parsed_failed_num,
                            'download_failed_num': self.download_failed_num,
                            'spider_id': self.spider_id,
                            'worker_id': self.worker_id,
                            'config_id': self.config_id,
                            'config_name': self.config_name,
                            'siteName': self.siteName,
                            'job_id': self.job_id
                            }
                # duanyifei add 2017/4/19 增加爬虫结束前调用接口
                try:
                    self.before_stoped(log_data=response)
                except Exception as e:
                    log.logger.exception(e)
                # 防止由于redis故障而导致的减慢配置运行速度 此时可设置 log_db 为空
                if self.log_db:
                    util.save_log(self.log_db, str(self.config_id), response)
                # 监控信息不保存到redis
                response.update({
                    'detail_page_record_list': self.detail_page_record_list[:100],
                    'error_reason': dict(error_reason),
                })
                #
                # 保存监控信息到 redis  指定监控并且非debug模式生效
                if self.monitor_on and not self.debug:
                    util.save_monitor_log(self.log_db, "config_monitor_data", response)
                    log.logger.info("config_monitor_info is saved !!!")

                # 打印爬虫日志信息
                if self.debug:
                    for k, v in response.iteritems():
                        if isinstance(v, (basestring, int, float)):
                            print "%s : %s" % (k, str(v))
                        else:
                            if k in ('detail_page_record_list',):
                                limits = 10
                                # print "%s : 总数 %s 最大显示条数 %s" % (k, len(v), limits)
                                v = v[:limits]
                                print pprint.pformat(v)
                            else:
                                print "%s : \n %s" % (k, pprint.pformat(v))

                self.job_event.set()
            #
            self.lock.release()
            return True
        return False

    # duanyifei 2016-5-23
    def check_detail_field_value(self, result):
        '''
        参数result为解析页面返回值
        此函数作用为记录页面返回值解析错误的字段

        错误定义:
            字符串字段返回值为空
            visitCount, replyCount 返回值为-1
            ctime和gtime相差 1s 内

        '''
        if not result:
            return True
        if not isinstance(result, list):
            log.logger.error('parse_detail_page() error: return value is not list or dict')
            return True
        new_result = []
        g_c = datetime.timedelta(seconds=1)
        for post in result:
            if not post:
                continue
            url = post.get('url')
            dic = {'url': url}
            ctime, gtime = post.get('ctime'), post.get('gtime')
            # duanyifei 2016/10/26 add  判断 ctime 是否存在
            if not post.get('data_db', '').startswith('rocketmq://') and not ctime or (isinstance(ctime, datetime.datetime) and ctime.microsecond != 0):
                dic.update({'ctime': str(ctime)})
                self.failed_info['ctime'].append("%s : %s" % ('ctime', url))

            for k, v in post.iteritems():
                error_flag = 0
                k = str(k)
                if k == 'url':
                    pass
                elif isinstance(v, datetime.datetime):
                    continue
                elif isinstance(v, str):
                    if not v:
                        error_flag = 1
                elif k in ('visitCount', 'replyCount'):
                    if isinstance(v, list):
                        count = v[0].get('count')
                    else:
                        count = v
                    if count < 0:
                        v = count
                        error_flag = 1
                else:
                    continue
                if error_flag:
                    dic.update({k: v})
            if len(dic.keys()) > 1:
                new_result.append(dic)
        self.detail_page_record_list += new_result
        return True

    def get_field_type(self):
        basestring_type_list = ['url']
        str_type_list = ['title', 'content', 'author', 'source', 'siteName', 'channel', 'html', 'summary']
        datetime_type_list = ['ctime', 'gtime']
        list_type_list = ['video_urls', 'pic_urls']
        list_or_int_type_list = ['visitCount', 'replyCount']
        dic = dict()
        dic.update({}.fromkeys(basestring_type_list, basestring))
        dic.update({}.fromkeys(str_type_list, str))
        dic.update({}.fromkeys(datetime_type_list, (datetime.datetime, int)))
        dic.update({}.fromkeys(list_type_list, list))
        dic.update({}.fromkeys(list_or_int_type_list, (list, int)))
        return dic

    def check_detail_field_type(self, post):
        '''对详情页返回值字段类型进行检查'''
        flag = True
        error = {}
        for k, v in post.iteritems():
            if k in self.field_type_dic.keys():
                should_type = self.field_type_dic.get(k)
                if not isinstance(v, should_type):
                    flag = False
                    if k == 'url':
                        error.update({'url_type': str(type(v))})
                    else:
                        error.update({k: str(type(v))})
                    if self.debug:
                        log.logger.error(
                            util.RR(k) + " TYPE ERROR, should be {}, but found ".format(should_type) + util.RR(
                                "{}".format(type(v))))
                    else:
                        log.logger.error(
                            "{} TYPE ERROR, should be {}, but found {}".format(k, self.field_type_dic.get(k), type(v)))
        if not flag:
            url = post.get('url', '')
            error.update({'url': url})
            self.field_type_failed_record.append(error)
        return flag

    def add_field(self, response, result=[]):
        if response is None:
            return result

        if isinstance(result, dict):
            result = [result]
        result = copy.deepcopy(result)

        def get_fields(response):
            try:
                doc = myreadability.Document(response.content)
                channel = doc.get_channel()
                if hasattr(doc, 'source'):
                    retweeted_source = doc.source
                if not retweeted_source:
                    retweeted_source = 'error_source'
                if not channel:
                    channel = 'error_channel'
            except Exception as e:
                log.logger.error("add_field() error: %s" % e)
                log.logger.error(traceback.format_exc())
                log.logger.exception(e)
                retweeted_source = 'error_source'
                channel = 'error_channel'
            return {'retweeted_source': retweeted_source, 'channel': channel}

        retweeted_source = ''
        channel = ''

        for post in result:
            if 'retweeted_source' not in post:
                if not retweeted_source:
                    fields = get_fields(response)
                    retweeted_source = fields.get('retweeted_source')
                    channel = fields.get('channel')
                    if retweeted_source and retweeted_source != 'error_source':
                        post.update({'retweeted_source': retweeted_source})
                elif retweeted_source == 'error_source':
                    pass
                else:
                    post.update({'retweeted_source': retweeted_source})
            if 'channel' not in post:
                if not channel:
                    fields = get_fields(response)
                    retweeted_source = fields.get('retweeted_source')
                    channel = fields.get('channel')
                    if channel and channel != 'error_channel':
                        post.update({'channel': channel})
                elif channel == 'error_channel':
                    pass
                else:
                    post.update({'channel': channel})
        return result

    # duanyifei 2017/02/16 add
    def add_html(self, response, result=[]):
        html = ''
        try:
            html = response.content
        except Exception as e:
            log.logger.error("add_html() error: %s" % e)

        if isinstance(result, dict):
            result = [result]
        result = copy.deepcopy(result)

        for post in result:
            if 'html' not in post:
                post.update({'html': html})
            # 2017/09/01 段毅飞 将html用repr转码
            # html = repr(post.get('html', ''))
            # post.update({'html': html})
            # 2017/11/16  段毅飞　增加html_base64字段　html字段置为空
            html = post.get("html")
            html_base64 = base64.encodestring(zlib.compress(html))
            post.update({
                "html": "",
                "html_base64": html_base64,
            })
        return result

    # 2016/12/20 duanyifei add
    def add_time(self, result=[]):
        '''
        注意: 时间是UTC时间 涉及到日期的增减 因此统一化为本地时间进行处理
        处理无 时分秒 的发布时间格式
        规则：
            临界值采集时间为 0 点 0 分 0 秒时不予处理
            其他时间 按照采集时间减去1分钟 赋值给 ctime
        '''
        if not result:
            return []
        utcnow = datetime.datetime.utcnow()
        result = copy.deepcopy(result)
        for post in result:
            ctime = post.get('ctime')
            gtime = post.get('gtime', utcnow)
            if isinstance(gtime, int) or isinstance(ctime, int):
                continue
            # 没有时间的不做处理
            if ctime:
                # 转换为本地时间 按北京时间处理
                ctime = ctime + datetime.timedelta(hours=8)
                gtime = gtime + datetime.timedelta(hours=8)
                # 0点临界值不做处理
                if gtime.strftime("%H%M%S") == '000000':
                    pass
                elif ctime.strftime("%H%M%S") == '000000':
                    span_time_day = (gtime - ctime).days
                    if span_time_day > 0:
                        # 第二天采集
                        ctime = ctime.replace(hour=23, minute=59, second=59)
                    else:
                        # 当天采集，分钟减 1
                        gtime = gtime - datetime.timedelta(minutes=1)
                        ctime = ctime.replace(hour=gtime.hour, minute=gtime.minute, second=gtime.second)
                    ctime = ctime - datetime.timedelta(hours=8)
                    post.update({
                        'ctime': ctime,
                    })
        return result

    # 2017/7/3 duanyifei add
    def add_config_info(self, result=[]):
        """返回数据中追加配置文件相关信息"""
        # 处理
        self._conf_info.pop("config_content", "")
        #
        for post in result:
            post.setdefault("config_info", self._conf_info)
        return result

    def parse_detail_by_url(self, request=None):
        '''
        参数url指向一个详情页，下载并分析该页面详情；并统计分析结果；
        返回值为一个二元元组；第一个值表示所有详情页是否下载解析完毕，第二个值表示是否有下一页要抓取；
        '''
        request = copy.deepcopy(request)
        url = request.get('url') if isinstance(request, dict) else request
        next_urls = []

        result = {}
        parse_success = True

        response = self.download(request, func_name='parse')
        try:
            result = self.parse_detail_page(response, request)
            result = self.before_save_data(result, handle=False)
        except Exception as e:
            # duanyifei 2016-5-24
            e_detail = traceback.format_exc()
            if self.debug:
                print util.R(e_detail)
            else:
                log.logger.error(e_detail)
            exc_dic = {'detail': e_detail, 'url': url, 'e_name': util.get_type_str(e)}
            self.exceptions_info_list.append(exc_dic)
            # duanyifei 2016-5-24
            parse_success = False
        # 下载网页失败
        if result is None:
            self.increase_download_failed_num()
            log.logger.info("DOWNLOAD_FAILED; url:%s" % url)
            res = self.spider_finished()
            return res, next_urls

        if not result:
            parse_success = False
        else:
            if isinstance(result, dict):
                result = [result]
            if isinstance(result, list):
                new_result = []
                for item in result:
                    if isinstance(item, dict):
                        next_urls += item.pop('next_urls', [])
                        item.setdefault('url', url)
                        # 把得到的deque做成一个字典，这里可能会产生一点小冲突，但是可以接受
                        channel_url_detail_url_dict = dict(list(self.detail_url_channel_url_deque))
                        # 使用setdefault功能，不改变指定值
                        item.setdefault('channel_url', channel_url_detail_url_dict.get(url, " "))
                        # 值存在检查
                        for key, value in item.items():
                            if not value:
                                parse_success = False
                                log.logger.info("PARSE_DETAIL_FAILED; parse %s failed; url:%s" % (util.RR(key), url))
                                if self.parse_failed.get(key, True):
                                    self.parse_failed[key] = True
                                    self.failed_info[key].append("%s : %s" % (key, url))
                            else:
                                self.parse_failed[key] = False
                        # 类型检查
                        if not self.check_detail_field_type(item):
                            parse_success = False
                            continue
                        new_result.append(item)
                result = new_result
        if parse_success:
            self.increase_parsed_success_num()
        else:
            self.increase_parsed_failed_num()
        # save data to db by data_queue
        res = {'url': url,
               'config_id': self.config_id,
               'info_flag': self.info_flag,
               'siteName': self.siteName,
               'data_db': self.data_db,
               'spider_id': getattr(setting, 'SPIDER_IP', self.spider_id)}

        g_c = datetime.timedelta(seconds=1)
        # 标题解析成功时将该数据入库，否则丢弃;
        if isinstance(result, dict):
            result = [result]
        if isinstance(result, list):
            new_result = []
            info_flag = 0
            try:
                info_flag = int(getattr(self, 'info_flag', 0))
            except Exception as e:
                log.logger.error("获取 info_flag error: %s, config_id: %s" % (e, self.config_id))

            # 限制 info_flag 不为 0401(微博)
            if info_flag != 401 and result:
                _result = []
                # 2017/02/16 duanyifei add_html
                try:
                    if response:
                        _result = self.add_html(response, result)
                    if _result:
                        result = _result
                except Exception as e:
                    log.logger.error("add_html() error: %s" % e)
                    log.logger.exception(e)
                    # 2017/02/16 duanyifei add_html

            for item in result:
                if isinstance(item, dict):
                    if item.get('title', ''):
                        res1 = res.copy()
                        res1.update(item)

                        # item 大小校验 李际朝 2018/04/12添加代码
                        def get_size(it):
                            s1 = len(it.get("html", ""))
                            s2 = len(it.get("content_xml", ""))
                            s3 = len(it.get("content", ""))
                            s4 = len(it.get("html_base64", ""))
                            # log.logger.debug("html: {} content_xml：{}content：{}html_base64：{}".format(s1, s2, s3, s4))
                            return s1 + s2 + s3 + s4

                        total_size = get_size(item)
                        # log.logger.debug("Total size: {}".format(total_size))
                        # if total_size > 8 * 1024 * 1024:  # 不要超过8M字节
                        if total_size:
                            # log.logger.debug("data is too big: %d, %s" % (total_size, item.get("url", "")))
                            # 始用pop(key, None)可以避免keyError
                            item.pop('html', None)
                            item.pop('html_base64', None)
                            item.pop('content_xml', None)
                            log.logger.debug("page_max: {}".format(get_size(item)))
                        # item 大小校验 李际朝 2018/04/12添加代码

                        new_result.append(res1)
                        #
                        if self.debug or (setting.SHOW_DATA and 'tty' in setting.STDOUT_PATH):
                            print util.B('\n {}'.format('###########################'))
                            ctime, gtime = res1.get('ctime'), res1.get('gtime')
                            if isinstance(gtime, int):
                                g_c = 1
                            time_error = 1 if gtime - ctime < g_c else 0
                            for k, v in res1.iteritems():
                                # 调试模式不显示 html 字段 内容太多
                                if k in ['html', 'html_base64']:
                                    continue
                                if not v:
                                    print util.R('{:>10.10}'.format(k)) + ': {}'.format(v)
                                elif (k in ('ctime',) and time_error):
                                    print util.R('{:>10.10}'.format(k)) + ': ' + util.RR('{}'.format(v))
                                else:
                                    # print '{:>10.10} : {}'.format(str(k), str(v))
                                    pass

            # 2016/12/20 duanyifei check ctime and add hour.minute.second start
            # 放在入库之前 不显示在调试模式中
            try:
                _result = self.add_time(new_result)
                if _result:
                    new_result = _result
            except Exception as e:
                log.logger.error("add_time() error: {}".format(e))
                log.logger.exception(e)
            # 2016/12/20 duanyifei check ctime and add hour.minute.second end

            if new_result:
                try:
                    new_result = self.add_config_info(new_result)
                except Exception as e:
                    log.logger.error('add_config_info() error: %s' % e)
                    log.logger.exception(e)
                self.crawler_data_queue.put(self.before_save_data(new_result))

        # duanyifei 2016-5-23
        # 指定监控或者debug模式下 收集详情页错误字段信息
        if self.monitor_on or self.debug:
            try:
                self.check_detail_field_value(result)
            except Exception as e:
                log.logger.exception(e)
        # duanyifei 2016-5-23
        #
        self.increase_new_data_num(number=len(next_urls))
        #
        res = self.spider_finished()
        #
        return res, next_urls


if __name__ == "__main__":
    error_response = {
        'spider_id': '12',
        'config_id': '34',
        'config_name': 'test',
        'error_info': [(3, 'error1'), (3, '234')]
    }
    j_data = json.dumps(error_response)
    data = {"crawl_result": j_data}
    e_data = urllib.urlencode(data)
    url = "http://192.168.110.24/task.php"
    try:
        resp = urllib2.urlopen(url, e_data, timeout=15)
    except Exception as e:
        log.logger.info("send crawl result to %s failed: %s" % (url, e))
        print "failed"
    else:
        print resp.read()
        print "ok"
