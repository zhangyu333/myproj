#!/usr/bin/env python
# coding:utf-8

#############################################################################


'''
文件名：downloader.py
功能：该模块实现网页下载； 
　　　目前实现的功能有：
　　　　　随机切换代理
      支持　content-encoding：　gzip　deflate
      retry
      redirect
代码历史：
'''

import gevent
import gevent.queue
#from gevent import monkey
 
#monkey.patch_all()

import json
import time
import copy
import random
import logging
import urlparse
import traceback

import requests

import log
import util
import proxy
import setting


def retry(ExceptionToCheck, tries=1, delay=1, backoff=2):
    """
    下载失败重试装饰器
    参数ExceptionToCheck表示当该异常发生时，重新下载该网页
    参数tries表示最大重试次数
    参数delay表示初始等待重试间隔
    参数backoff表示时间间隔系数；每重试一次，时间间隔乘以该参数
    """
    def deco_retry(f):
        def f_retry(self, *args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 0:
                try:
                    return f(self, *args, **kwargs)
                except ExceptionToCheck as e:
                    log.logger.exception(e)
                    log.logger.error("%s, Retrying in %d seconds..." % (util.B(str(e)), mdelay))
                    time.sleep(0.5)
                    mtries -= 1
                    mdelay *= backoff
                    lastException = e
                    # 强制更新代理
                    # self.random_set_proxy(request, force=True)
            raise lastException
        return f_retry # true decorator
    return deco_retry


class ProxyItem(object):
    """
    """
    def __init__(self, proxy_type=None, host=None, proxy_max_num=5):
        """
        初始化代理类
        """
        # 每个代理最多可连续使用次数
        self.max_reused_num = setting.PROXY_MAX_NUM if proxy_max_num <= 0 else proxy_max_num
        # 记录当前代理已使用次数
        self.proxy_counter = 0
        self.proxy_type = proxy_type or 'http'
        self.host = host
    
    def get_proxy(self):
        """
        返回该代理类型和主机地址，同时将计数器加1
        """
        
        if self.proxy_counter >= self.max_reused_num:
            return None, None
        self.proxy_counter += 1
        return self.proxy_type, self.host
    
    def is_valid(self):
        return self.proxy_counter < self.max_reused_num
    
    def __str__(self):
        return "%s:%s" % (self.proxy_type, self.host)
    
class ProxyManager(object):
    """
    """
    def __init__(self, proxy_max_num=10, available_proxy=20, proxy_url=None):
        """
        初始化代理管理器类
        """
        #代理最多可连续使用次数
        self.proxy_max_num = setting.PROXY_MAX_NUM if proxy_max_num <= 0 else proxy_max_num
        
        #最多可用代理数目
        self.maxsize = setting.PROXY_AVAILABLE if available_proxy <= 0 else available_proxy
        
        self.proxy_url = proxy_url
        #LIFO
        self.proxy_queue = gevent.queue.LifoQueue(maxsize=self.maxsize*5)
        self.init_proxy_queue()
        #代理黑名单,保存下载失败时使用的代理
        self.black_proxies = set()
    
    def random_choice_proxy(self):
        """
        随机从self.proxy_list获取一个代理，并将该代理从self.proxy_list删除
        如果self.proxy_list元素较少时，重新加载代理
        """
        #重新加载代理
        if self.proxy_list and len(self.proxy_list) <= 1:
            self.proxy_list = proxy.get_proxy(self.proxy_url)
        #随机从proxy_list获取一个代理，并将该代理从proxy_list删除
        try:
            index = int(random.random() * len(self.proxy_list))
            proxy_type, host, port = self.proxy_list.pop(index)
        except:
            return None, None
        else:
            proxy_host = "%s:%s" % (host, port)
            return proxy_type, proxy_host
        # try:
        #     index = int(random.random() * len(self.proxy_list))
        #     proxy_type, host, port = self.proxy_list[index]
        # except:
        #     return None, None
        # else:
        #     proxy_host = "%s:%s" % (host, port)
        #     return proxy_type, proxy_host

    def update_black_proxies(self, host):
        """
        保存所有不可用的代理或者下载超时的代理;每添加一个不可用代理，则随机取一个新的代理放到proxy_queue中
        同时，返回新获取的代理
        """
        if host:
            self.black_proxies.add(host)
        #
        return self.random_choice_proxy()
    
    def init_proxy_queue(self):
        """
        从代理服务器获取代理，初始化代理队列
        """
        #从代理服务器获取代理
        self.proxy_list = proxy.get_proxy(self.proxy_url)
        if not self.proxy_list:
            return 
        for _ in xrange(self.maxsize):
            proxy_type, proxy_host = self.random_choice_proxy()
            if proxy_type is not None and proxy_host is not None:
                proxy_item = ProxyItem(proxy_type, proxy_host, self.proxy_max_num)
                self.put_proxy(proxy_item)

    def put_proxy(self, proxy_item):
        """
        将代理放入代理队列
        """
        try:
            self.proxy_queue.put(proxy_item, block=False)
        except gevent.queue.Full:
            log.logger.debug("proxy pool is full, discarding proxy: %s"%proxy_item)
    
    def get_proxy(self):
        """
        从代理队列中取出一个代理，判断该代理有消息；如果是有效代理，将给代理放回代理队列并返回该代理
        """
        proxy_item = None
        try:
            proxy_item = self.proxy_queue.get(False)
        except gevent.queue.Empty as e:
            proxy_type, proxy_host = self.random_choice_proxy()
            return ProxyItem(proxy_type, proxy_host, self.proxy_max_num)
        else:
            if proxy_item.is_valid():
                return proxy_item
            else:
                return self.get_proxy()


class Downloader(object):
    '''下载器'''
    def __init__(self, proxy_enable=setting.PROXY_ENABLE,
                 proxy_max_num=setting.PROXY_MAX_NUM,
                 available_proxy=setting.PROXY_AVAILABLE,
                 proxy_url=setting.PROXY_URL,
                 cookie_enable=setting.COOKIE_ENABLE, 
                 timeout=setting.HTTP_TIMEOUT, **kwargs):
        super(Downloader, self).__init__()
        self.cookie_enable = cookie_enable
        self.proxy_enable = proxy_enable
        self.headers = {
                        "Accept": "text/html, application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8",
                        "User-Agent": setting.USER_AGENT,
                        }
        self.proxy_url = proxy_url
        if self.proxy_enable:
            self.proxy_manager = ProxyManager(proxy_max_num, available_proxy, proxy_url)
        if timeout > 120 or timeout <= 0:
            self.timeout = 30
        else:
            self.timeout = timeout
        #
        self.session = requests.Session()
        a = requests.adapters.HTTPAdapter(pool_connections=1000,
                                          pool_maxsize=1000,
                                          max_retries=0)
        self.session.mount('http://', a)
        self.session.mount('https://', a)
        self.config_id = ''
        # requests模块支持的参数列表
        self.requests_module_kwargs = ["params", "data", "json", "headers", "cookies", 
                                       "files", "auth", "timeout", "allow_redirects", 
                                       "proxies", "verify", "stream", "cert"]
        
        self.keep_status_code = False

    def init_proxy_success(self):
        """
        返回初始化代理结果，成功返回True,失败返回False;
        """
        if self.proxy_enable:
            if self.proxy_manager.proxy_queue.qsize() > 0:
                return True
        return False
    
    @retry(Exception)
    def _download(self, request, **kwargs):
        request = copy.deepcopy(request)
        url = request.get('url') if isinstance(request, dict) else request
        response = None
        if self.proxy_enable:
            proxy_item = self.proxy_manager.get_proxy()
            proxy_type, proxy_host = proxy_item.get_proxy()
            if proxy_host is not None:
                # use http as the only proxy schema
                proxy = "%s://%s" % ("http", proxy_host)
                proxies = {'http': proxy, 'https': proxy}
            else:
                proxies = None
        else:
            proxies = None
        
        # 异常是否在本函数内发生 标志位
        is_exc = 0
        try:
            timeout = gevent.Timeout(self.timeout + 1)
            timeout.start()
            try:
                if 'proxies' not in kwargs:
                    kwargs.update(proxies=proxies)

                kwargs.update({
                    'stream':True,
                    'timeout':self.timeout,
                    })

                default_method = 'POST' if 'data' in kwargs else 'GET'

                keep_status_code = 0

                if isinstance(request, dict):
                    try:
                        if request.get('meta', {}).get('keep_status_code', self.keep_status_code):
                            keep_status_code = 1
                    except:
                        pass
                    method = request.get('method')
                    default_method = method if method is not None else default_method
                    kwargs.update(request)
                    for key in kwargs.keys():
                        if key not in self.requests_module_kwargs:
                            kwargs.pop(key)
                time.sleep(1)
                r = self.session.request(default_method, url, **kwargs)
                response = r
                if r.status_code not in (200, 404, 410):
                    log.logger.warning("return status_code %s  warning url: %s"%(util.BB(r.status_code), str(url)))
                    if not keep_status_code:
                        r.raise_for_status()
                elif r.status_code in (404, 410):
                    log.logger.warning("return status_code %s  warning url: %s"%(util.BB(r.status_code), str(url)))
                response.content

                #保存当前代理
                if self.proxy_enable:
                    self.proxy_manager.put_proxy(proxy_item)
                try:
                    response.proxies = kwargs.get('proxies')
                except Exception as e:
                    log.logger.error("response对象增加代理属性失败 %s"%e)
            except requests.exceptions.Timeout, e:
                is_exc = 1
                raise e
            except requests.exceptions.RequestException as e:
                is_exc = 1
                raise e
            except Exception as e:
                is_exc = 1
                raise e
            else:
                r.close()
        except gevent.Timeout as e:
            is_exc = 1
            raise requests.exceptions.Timeout
        except requests.exceptions.RequestException as e:
            is_exc = 1
            raise e
        except Exception as e:
            is_exc = 1
            raise e
        finally:
            timeout.cancel()
            #try:
                #proxy_ip = ""
                #if proxies:
                    #proxy_ip = ",".join([urlparse.urlparse(x).netloc for x in proxies.values()])
                #_log_info = {
                    #"proxies": proxies,
                    #"proxy_ip": proxy_ip,
                    #"url": url,
                    #"proxy_url": self.proxy_url if proxy_ip else "",
                    #"status_code": response.status_code if response is not None else -1,
                    #"config_id": self.config_id,
                    #"kafka_topic": "spider_proxy",
                    #}
                #if response and response.status_code == 200:
                    ## 不关心正常的
                    #_log_info.pop('url', '')
                #if is_exc:
                    #_log_info.update({
                        #"exc_text": util.filter_exc_text(traceback.format_exc()),
                        #})
                    #log.logger.error(json.dumps(_log_info))
                #else:
                    #log.logger.info(json.dumps(_log_info))
            #except Exception as e:
                #log.logger.exception(e)
        
        return response

    def download(self, request, **kwargs):
        headers = kwargs.get('headers',{})
        self.headers.update(headers)
        kwargs.update(headers=self.headers)
        response = None
        try:
            response = self._download(request, **kwargs)
        except gevent.Timeout as e:
            #log.logger.debug("gevent.Timeout: %s : %s"%(url, str(e)))
            #print 'gevent.Timeout: ', str(e)
            pass
        except requests.exceptions.Timeout as e:
            #log.logger.debug(" requests.Timeout: %s : %s;"%(str(e), url))
            #print 'requests.Timeout', str(e)
            pass
        except requests.exceptions.RequestException as e:
            #log.logger.debug("requests.RequestException: %s : %s"%(e, url))
            #print 'RequestException', str(e)
            pass
        except Exception as e:
            #log.logger.debug("download %s failed; reason: %s"%(url, e))
            #print 'Exception: ', str(e)
            pass
        #print len(response)
        return response


if __name__ == '__main__':
#     item = ProxyItem('http', '192.168.1.1:80', 2)
#     print item.is_valid()
#     print item.get_proxy()
#     
#     print item.is_valid()
#     print item.get_proxy()
#     
#     print item.is_valid()
#     print item.get_proxy()
#     pm = ProxyManager(2,2)
#     
#     p = pm.get_proxy()
#     print p.get_proxy()
#      
#     proxy_item = ProxyItem('http', '112.84.130.13:80', 2)
#     pm.put_proxy(proxy_item)
# 
#     proxy_item = ProxyItem('http', '112.84.130.13:80', 2)
#     pm.put_proxy(proxy_item)
#     p = pm.get_proxy()
#     print p.get_proxy()
#     
#     p = pm.get_proxy()
#     print p.get_proxy()
#     
#     p = pm.get_proxy()
#     print p.get_proxy()
#     
#     p = pm.get_proxy()
#     print p.get_proxy()
    
#     urls = ["http://tieba.baidu.com/p/2650465863", 'http://tieba.baidu.com/p/2245454220', 'http://tieba.baidu.com/p/3022141148']*2
#     d = Downloader(True, 3,3, timeout=2)
#     
#     from gevent import po
#     ol
#     pool = pool.Pool(6)
#     t1 = time.time()
#     for url in urls:
#         pool.spawn(d.download, url)
#     pool.join()
#     print "gevent.pool: ", time.time() - t1
    
#     t1 = time.time()
#     jobs = [gevent.spawn(d.download, url) for url in urls]
#     gevent.joinall(jobs)
#     print "gevent.spawn: ", time.time() - t1

#     from gevent import threadpool
#     t1 = time.time()
#     pool = threadpool.ThreadPool(6)
#     for url in urls:
#         pool.spawn(d.download, url)
#     pool.join()
#     print "thread: ", time.time() - t1
#    url = 'http://bbs.jztele.com/thread-3575106123-1-1.html'
    url = 'http://tieba.baidu.com/p/3231819545'
#     header = {'Accept':'*/*',
#               'User-Agent':'python-requests/2.2.1 CPython/2.7.6 Windows/7'}
    d = Downloader(True, 3,3, timeout=20)
    response = d.download(url)
    print(response.status_code)
#     print response.request.headers
    
#     import requests
#     headers = {"Accept":"text/html, application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8",
#     "User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64; rv:29.0) Gecko/20100101 Firefox/29.0",
#     "Referer":"http://www.0595bbs.cn/forum-61-1.html?order=createdat",
#     "Accept-Language":"zh-cn,zh;q=0.8,en-us;q=0.5,en;q=0.3"
#     }
#     proxies = {'http':'http://111.206.81.248:80'}
#     response = requests.get(url, headers=headers)
# #    response = requests.get(url)
#     
#     print response.text
# #     print response.request.headers
# #     print response.request.url
#     print response.url
