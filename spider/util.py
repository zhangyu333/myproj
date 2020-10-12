#!/usr/bin/env python
# coding:utf-8


#############################################################################


'''
文件名：util.py
功能：工具函数文件 

代码历史：
'''
import os
import re
import sys
import time
import copy
import datetime
import functools
import HTMLParser
import urlparse    
import json
from urllib import urlencode
import requests
import redis
import threading
from lxml.html.clean import Cleaner
import sys
reload(sys)
sys.setdefaultencoding('utf8')

try:
    from termcolor import colored
except ImportError:
    def colored(text, color=None, on_color=None, attrs=None): return text

import log


is_py3 = sys.version_info.major == 3
if is_py3:
    string_types = (str, bytes)
else:
    string_types = (basestring, )

conn_pool = redis.ConnectionPool(host='redis-duptieba-1.istarshine.net.cn', port=6379, db=3)
connection = redis.StrictRedis(connection_pool=conn_pool)


def synchronized(func):
    func.__lock__ = threading.Lock()

    def lock_func(*args, **kwargs):
        with func.__lock__:
            return func(*args, **kwargs)

    return lock_func



class Request(object):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.get('request', None)
        

def filter_exc_text(exc_text):
    exc_text_list = exc_text.split("\n")
    if len(exc_text_list) <= 9:
        return exc_text
    else:
        return "\n".join(exc_text_list[:6] + exc_text_list[-3:])
    return exc_text


def canonicalize_url(url, keep_fragment=True):
    """
    规范化url:对url中的query字段重新排序，
    避免http://xxx.com/123.html?b=1&a=3和http://xxx.com/123.html?a=3&b=1作为两个url存在
    """
    import urllib
    uri = urlparse.urlsplit(url)
    query_args = urlparse.parse_qsl(uri.query,True)
    query_args.sort()
    query_args = urllib.urlencode(query_args)
    if keep_fragment:
        return urlparse.urlunsplit((uri.scheme, uri.netloc, uri.path, query_args, uri.fragment))
    else:
        return urlparse.urlunsplit((uri.scheme, uri.netloc, uri.path, query_args, ''))

def clear_special_xpath(data, xp):
    '''
    删除指定 xpath 数据
    仅作用于 htmlparser.Parser 对象
    '''
    data = copy.deepcopy(data)
    result = data._root.xpath(xp)
    try:
        for i in result:
            i.getparent().remove(i)
    except:
        pass
    return data

# 取个别名
clear_xpath = clear_special_xpath

def filter_style_script(text):
    """去除注释 style script"""
    html_cleaner = Cleaner(scripts=True, javascript=True, comments=True, style=True,
                    links=False, meta=False, page_structure=False, processing_instructions=False,
                    embedded=False, frames=False, forms=False, annoying_tags=False, remove_tags=None,
                    remove_unknown_tags=False, safe_attrs_only=False)
    text = html_cleaner.clean_html(text)
    return text


# mongodb://[username:password@]host1[:port1][,host2[:port2],...
# [,hostN[:portN]]][/[database][?options]]
def from_url(uri):
    """
    以uri形式连接数据库，并返回相应可以操作数据库的对象
    """
    # duanyifei 20170515
    uri = uri.strip("_")
    #
    if uri.startswith('zmq://'):
        # return DataQueuePipeline(uri)
        return ''

    elif uri.startswith('mongodb://'):
        return MongoPipeline(uri)
    
    elif uri.startswith('mysql://'):
        return MysqlPipeline(uri)
    
    elif uri.startswith('redis://'):
        return RedisPipeline(uri)
    elif uri.startswith('rocketmq://'):
        # data_db = "rocketmq://192.168.141.12:9876;192.168.141.14:9876;192.168.141.16:9876/yg_data"
        #data_db = "rocketmq://127.0.0.1/0/zhaotoubiao_biangeng_info"
        data_db = 'redis://' + uri.split('rocketmq://')[-1]
        return RedisPipeline(data_db)
    elif uri.startswith('kafka://'):
        return KafkaPipeline(uri)


    else:
        raise Exception('unknow uri <{}>'.format(uri))

    return None

def fromtimestamp(timestamp):
    return datetime.datetime.fromtimestamp(float(timestamp)) - datetime.timedelta(hours=8)

def get_type_str(instance):
    '''获取实例的类型名字'''
    return getattr(type(instance), '__name__', '')

def get_current_file_path():
    '''
    获取当前文件所在路径
    '''
    path = os.path.dirname(os.path.abspath(sys.path[0]))
    if os.path.isdir(path):
        return path
    elif os.path.isfile(path):
        return os.path.dirname(path)

def get_keywords(key_start, limits, connection=connection, key_keywords=None):
    '''
    '''
    if key_keywords is None:
        key_keywords = 'all_user_keywords'
    
    start = connection.get(key_start)
    
    start = 0 if start is None else int(start)
    
    len = connection.llen(key_keywords)
    if len == 0:
        return []
#    elif len == 1:
#        return [connection.lindex(key_keywords, 0)]
    
    if start >= len:
        start = 0
        new_start = (start + limits) % len
        end = new_start - 1
        connection.set(key_start, new_start)
        return connection.lrange(key_keywords, start, end)
    else:
        if start + limits <= len:
            new_start = (start + limits) % len
            end = new_start - 1
            connection.set(key_start, new_start)
            return connection.lrange(key_keywords, start, end)
        elif start + limits <= 2 * len:
            new_start = (start + limits) % len
            end = new_start - 1
            connection.set(key_start, new_start)
            return connection.lrange(key_keywords, start, -1) + connection.lrange(key_keywords, 0, end)
        else:
            return connection.lrange(key_keywords, start, -1)

def get_one_result(pattern, string):
    try:
        result_tuple = re.compile(pattern).findall(string)
    except Exception:
        return None
    return result_tuple[0] if result_tuple else None
    
def get_one_result_c(p, string):
    try:
        result_tuple = p.findall(string)
    except Exception:
        return None
    return result_tuple[0] if result_tuple else None

def get_verify_code(img_name, type, url='http://192.168.164.108/caijicode/test.php'):
    '''
    获取验证图片中的信息,如果获取验证信息成功，将该图片删除
    img_name:图片名称，包含路径信息
    '''
    verify_code = ''
    if os.path.exists(img_name):
        with open(img_name, 'rb') as f:
            content = f.read()
            data = {
                "code":content,
                "type":type,
                }
            try:
                resp = requests.post(url, data)
                verify_code = resp.content
                print("---resp: %s" % verify_code)
            except Exception as e:
                log.logger.error("--get_verify_code() : %s"%e)
    return verify_code

def install_module(module_name, install="pip"):
    if install == "pip":
        resp = os.system("pip install %s" % module_name)
        return resp
    return 0

def is_re_match(pattern, string):
    '''
    '''
    m = re.match(pattern, string)
    return bool(m)

def is_variable(v):
    '''
    '''
    try:
        type(eval(v))
    except:
        return False
    return True

def keepalive(handle_func=None, interval=1):
    '''装饰器
    功能：
       捕获被装饰函数的异常并重新调用函数
       函数正常结束则结束
    装饰器参数：
       @handle_func:function
          异常处理函数 默认接收参数 e(异常对象), func(被装饰函数)
       @interval:number
          函数重启间隔
    '''
    def wrapper(func):
        @functools.wraps(func)
        def keep(*args, **kwargs):
            while 1:
                try:
                    result = func(*args, **kwargs)
                except Exception as e:
                    if handle_func:
                        handle_func(e, func)
                    time.sleep(interval)
                    continue
                break
            return result
        return keep
    return wrapper

def text_to_str(text, encoding='utf8'):
    '''
    将传入文本转换为str类型 兼容py2 py3
    '''
    if is_py3:
        if isinstance(text, bytes):
            text = text.decode(encoding)
    else:
        if isinstance(text, unicode):
            text = text.encode(encoding)
    return text        
        
    
def TimeDeltaYears(years, from_date=None):
    if from_date is None:
        from_date = datetime.datetime.now()
    try:
        return from_date.replace(year=from_date.year + years)
    except:
        # Must be 2/29!
        assert from_date.month == 2 and from_date.day == 29 # can be removed
        return from_date.replace(month=2, day=28,
                                 year=from_date.year+years)

def local_datetime(data):
    '''
    把data转换为日期时间，时区为东八区北京时间，能够识别：今天、昨天、5分钟前等等，如果不能成功识别，则返回datetime.datetime.now()
    '''
    dt = datetime.datetime.now()
    # html实体字符转义
    data = HTMLParser.HTMLParser().unescape(data)
    data = data.strip()
    if not data:
        return dt
    try:
        data = text_to_str(data)
    except Exception as e:
        log.logger.error("utc_datetime() error: data is not utf8 or unicode : %s" % data)

    # 归一化
    data = data.replace("年", "-").replace("月", "-").replace("日", " ").replace("/", "-").strip()
    data = re.sub("\s+", " ", data)
    
    year = dt.year
    
    regex_format_list = [
        # 2013年8月15日 22:46:21
        ("(\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{1,2}:\d{1,2})", "%Y-%m-%d %H:%M:%S", ""),
        
        # "2013年8月15日 22:46"
        ("(\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{1,2})", "%Y-%m-%d %H:%M", ""),

        # "2014年5月11日"
        ("(\d{4}-\d{1,2}-\d{1,2})", "%Y-%m-%d", ""),
        
        # "2014年5月"
        ("(\d{4}-\d{1,2})", "%Y-%m", ""),

        # "13年8月15日 22:46:21",
        ("(\d{2}-\d{1,2}-\d{1,2} \d{1,2}:\d{1,2}:\d{1,2})", "%y-%m-%d %H:%M:%S", ""),

        # "13年8月15日 22:46",
        ("(\d{2}-\d{1,2}-\d{1,2} \d{1,2}:\d{1,2})", "%y-%m-%d %H:%M", ""),

        # "8月15日 22:46:21",
        ("(\d{1,2}-\d{1,2} \d{1,2}:\d{1,2}:\d{1,2})", "%Y-%m-%d %H:%M:%S", "+year"),

        # "8月15日 22:46",
        ("(\d{1,2}-\d{1,2} \d{1,2}:\d{1,2})", "%Y-%m-%d %H:%M", "+year"),

        # "8月15日",
        ("(\d{1,2}-\d{1,2})", "%Y-%m-%d", "+year"),

        # "3 秒前",
        ("(\d+)\s*秒前", "", "-seconds"),

        # "3 秒前",
        ("(\d+)\s*分钟前", "", "-minutes"),

        # "3 秒前",
        ("(\d+)\s*小时前", "", "-hours"),

        # "3 秒前",
        ("(\d+)\s*天前", "", "-days"),

        # 今天 15:42:21
        ("今天\s*(\d{1,2}:\d{1,2}:\d{1,2})", "%Y-%m-%d %H:%M:%S", "date-0"),

        # 昨天 15:42:21
        ("昨天\s*(\d{1,2}:\d{1,2}:\d{1,2})", "%Y-%m-%d %H:%M:%S", "date-1"),

        # 前天 15:42:21
        ("前天\s*(\d{1,2}:\d{1,2}:\d{1,2})", "%Y-%m-%d %H:%M:%S", "date-2"),

        # 今天 15:42
        ("今天\s*(\d{1,2}:\d{1,2})", "%Y-%m-%d %H:%M", "date-0"),

        # 昨天 15:42
        ("昨天\s*(\d{1,2}:\d{1,2})", "%Y-%m-%d %H:%M", "date-1"),

        # 前天 15:42
        ("前天\s*(\d{1,2}:\d{1,2})", "%Y-%m-%d %H:%M", "date-2"),
        ]

    for regex, dt_format, flag in regex_format_list:
        m = re.search(regex, data)
        if m:
            if not flag:
                dt = datetime.datetime.strptime(m.group(1), dt_format)
            elif flag == "+year":
                # 需要增加年份
                dt = datetime.datetime.strptime("%s-%s"%(year, m.group(1)), dt_format)
            elif flag in ("-seconds", "-minutes", "-hours", "-days"):
                # 减秒
                flag = flag.strip("-")
                exec("dt = dt - datetime.timedelta(%s=int(m.group(1)))"%flag)
            elif flag.startswith("date"):
                del_days = int(flag.split('-')[1])
                _date = dt.date() - datetime.timedelta(days=del_days)
                _date = _date.strftime("%Y-%m-%d")
                dt = datetime.datetime.strptime("%s %s"%(_date, m.group(1)), dt_format)
            return dt
    else:
        log.logger.error("unknow datetime format: %s"%data)
    return dt

def utc_datetime(data):
    try:
        utc_dt = local_datetime(data) - datetime.timedelta(hours=8)
    except Exception as e:
        utc_dt = datetime.datetime.utcnow()
        log.logger.exception(e)
    return utc_dt

def R(x):
    return colored(x, 'red',    attrs=['bold'])
def G(x):
    return colored(x, 'green',  attrs=['dark', 'bold'])
def B(x):
    return colored(x, 'blue',   attrs=['bold'])
def Y(x):
    return colored(x, 'yellow', attrs=['dark', 'bold'])

def RR(x):
    return colored(x, 'white', 'on_red',    attrs=['bold'])
def GG(x):
    return colored(x, 'white', 'on_green',  attrs=['dark', 'bold'])
def BB(x):
    return colored(x, 'white', 'on_blue',   attrs=['bold'])
def YY(x):
    return colored(x, 'white', 'on_yellow', attrs=['dark', 'bold'])


def save_log(uri, key, data):
    try:
        conn = redis.StrictRedis.from_url(uri)
        data = json.dumps(data)
        conn.lpush(key, data)
        conn.ltrim(key, 0, 999)
    except Exception as e:
        log.logger.exception(e)
    return 

def save_monitor_log(uri, key, data):
    try:
        conn = redis.StrictRedis.from_url(uri)
        data = json.dumps(data)
        resp = conn.lpush(key, data)
        if resp > 100000:
            # 清理
            conn.delete(key)
    except Exception as e:
        log.logger.exception(e)
    return


ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def base62_encode(num, alphabet=ALPHABET):
    """Encode a number in Base X

    `num`: The number to encode
    `alphabet`: The alphabet to use for encoding
    """
    if (num == 0):
        return alphabet[0]
    arr = []
    base = len(alphabet)
    while num:
        rem = num % base
        num = num // base
        arr.append(alphabet[rem])
    arr.reverse()
    return ''.join(arr)

def base62_decode(string, alphabet=ALPHABET):
    """Decode a Base X encoded string into the number

    Arguments:
    - `string`: The encoded string
    - `alphabet`: The alphabet to use for encoding
    """
    base = len(alphabet)
    strlen = len(string)
    num = 0

    idx = 0
    for char in string:
        power = (strlen - (idx + 1))
        num += alphabet.index(char) * (base ** power)
        idx += 1

    return num
    
def mid_to_url(midint):
    '''
    '''
    midint = str(midint)[::-1]
    size = len(midint) / 7 if len(midint) % 7 == 0 else len(midint) / 7 + 1
    result = []
    for i in range(size):
        s = midint[i * 7: (i + 1) * 7][::-1]
        s = base62_encode(int(s))
        s_len = len(s)
        if i < size - 1 and len(s) < 4:
            s = '0' * (4 - s_len) + s
        result.append(s)
    result.reverse()
    return ''.join(result)

def url_to_mid(url):
    '''
    '''
    url = str(url)[::-1]
    size = len(url) / 4 if len(url) % 4 == 0 else len(url) / 4 + 1
    result = []
    for i in range(size):
        s = url[i * 4: (i + 1) * 4][::-1]
        s = str(base62_decode(str(s)))
        s_len = len(s)
        if i < size - 1 and s_len < 7:
            s = (7 - s_len) * '0' + s
        result.append(s)
    result.reverse()
    return int(''.join(result))



def retry(ExceptionToCheck, tries=3, delay=1, backoff=1):
    """
    函数重试装饰器
    参数ExceptionToCheck表示当该异常发生时，重新下载该网页
    参数tries表示最大重试次数
    参数delay表示初始等待重试间隔
    参数backoff表示时间间隔系数；每重试一次，时间间隔乘以该参数
    """
    def deco_retry(func):
        def wrapper(self, *args, **kwargs):
            mtries, mdelay = tries, delay
            count = 0
            while mtries > 0:
                try:
                    count += 1
                    kwargs.get('retries',{}).update({'count':count})
                    return func(self, *args, **kwargs)
                except ExceptionToCheck, e:
                    #print "%s, Retrying in %d seconds..."%(str(e), mdelay)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
                    lastException = e
            #print "exception : %s"%lastException
            raise lastException
        return wrapper # true decorator
    return deco_retry

@retry(Exception, 3, 2)
def _get_proxy_by_adsl(adsl_id=None, config_id=None):
    '''
    '''
    proxy = ''
    if adsl_id and config_id:
        proxy_url = "http://192.168.132.83:8080/proxy/get?adsl_id=%s&config_id=%s"%(adsl_id, config_id)
        try:
            resp = requests.get(proxy_url, timeout=15)
            proxy = resp.content
        except Exception as e:
            #print "--get_proxy_by_mid(mid=%s, sid=%s) failed: %s"%(mid, sid, e)
            raise e
        if not proxy:
            raise ValueError
    return proxy

def get_proxy_by_adsl(adsl_id, config_id):
    '''
    '''
    try:
        resp = _get_proxy_by_adsl(adsl_id, config_id)
    except Exception as e:
        log.logger.error("--get_proxy_by_adsl(adsl_id=%s, config_id=%s) failed: %s"%(adsl_id, config_id, e))
        resp = ''
    return resp

def release_proxy_by_adsl(adsl_id, config_id=None):
    '''
    '''
    try:
        url = "http://192.168.132.83:8080/proxy/release?adsl_id=%s&config_id=%s"%(adsl_id, config_id)
        resp = requests.get(url)
        return resp.content
    except:
        pass
    return '0'

def scp_img(src='', name='', dest='http://192.168.70.60/img.php', retries=3):
    '''
    send image to dest host
    '''
    if src:
        while retries>0:
            retries -= 1
            try:
                if not name:
                    name = os.path.basename(src)
                content = ''
                with open(src, 'rb') as f:
                    content = f.read()
                data = {
                    'name':name,
                    'content':content,
                }
                #print "name: ", name
                resp = requests.post(dest, data)
                print resp.content
                resp = json.loads(resp.content)
                if resp.get('path', ''):
                    return resp
            except Exception as e:
                log.logger.error("--scp_img failed: src:%s, Exception:%s"%(src, e))
                print "--scp_img() failed: %s"%e
    return {}

class MysqlPipeline(object):
    """
    """
    def __init__(self, uri):
        """
        """
        try:
            import MySQLdb
        except ImportError:
            log.logger.error("no module MySQLdb found")
        
        parsed = urlparse.urlparse(uri)
        host = parsed.hostname
        port = parsed.port or 3306
        user = parsed.username
        passwd = parsed.password
        
        db, table = parsed.path.strip('/').split('.')
        conn = MySQLdb.connect(
                                host=host,
                                port=port,
                                user=user,
                                passwd=passwd,
                                db=db,
                                charset='utf8'
                             )
        self.conn = conn
        self.table = table
        self.cursor = conn.cursor()
    
    def send(self, data, dest_json=False):
        """
        向数据库发送数据；
        """
        fields = []
        values = []
        for k, v in data.iteritems():
            fields.append(k)
            values.append(v)
        
        if self.conn:
            try:
                self.cursor.execute("""INSERT INTO %s(%s) VALUES (%s) """%(self.table, ','.join(fields), values))
                self.conn.commit()
            except Exception as e:
                log.logger.exception(e)
                return False
            else:
                return True
    
    def close(self):
        """
        """
        self.cursor.close()
        self.conn.close()
        self.cursor = self.conn = None


class MongoPipeline(object):
    """
    """
    def __init__(self, uri):
        """
        连接到monogodb数据库
        """
        import pymongo
        parsed = pymongo.uri_parser.parse_uri(uri)
        database = parsed['database']
        collection = parsed['collection']
        host, port = parsed['nodelist'][0]

        self.conn = pymongo.MongoClient(host=host, port=port)
        if database:
            self.db = self.conn[database]
        else:
            self.db = None
        if database and collection:
            self.collection = self.db[collection]
        else:
            self.collection = None
        #print "i am in mongodb", self.collection
        
    def send(self, data, dest_json=False):
        """
        """
        try:
            if self.collection:
#                self.collection.save(data)
                self.collection.insert(data)
        except Exception as e:
            log.logger.exception(e)
            return False
        return True
    
    def close(self):
        """
        """
        self.conn.close()
        self.conn = None


class RedisPipeline(object):
    """
    连接到redis数据库
    """
    def __init__(self, uri):
        """
        """
        import data_buffer
        self.db = data_buffer.create(uri)

    def send(self, data, dest_json=False):
        """
        """
        if isinstance(data, dict):
            self.db.push(data, dest_json=dest_json)
            return True
        elif isinstance(data, list):
            self.db.pushall(data, dest_json=dest_json)
            return True
    
    def close(self):
        """
        """
#        self.db.close()
        self.db = None


class KafkaPipeline(object):
    """
    连接到Kafka
    """
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(KafkaPipeline, "_instance"):
            with KafkaPipeline._instance_lock:
                if not hasattr(KafkaPipeline, "_instance"):
                    KafkaPipeline._instance = object.__new__(cls)
        return KafkaPipeline._instance

    def __init__(self, uri):
        """
        """
        self.ip = uri.split('kafka://')[-1].split('/')[0]
        self.ip = self.ip.split('#')
        self.topic  = uri.split('kafka://')[-1].split('/')[-1]
        # print self.ip
        # print self.topic
        # import kafka_client
        # self.producer = kafka_client.producer
        import json
        from kafka import KafkaProducer
        self.producer = KafkaProducer(
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            bootstrap_servers= self.ip,
            acks = 'all',
            buffer_memory=67108864,
            batch_size=262144,
            linger_ms=15,
            max_block_ms=120000,
        )

    def send(self, data, dest_json=False):
        """
        """
        if isinstance(data, dict):
            self.producer.send(self.topic,data)
            return True
        elif isinstance(data, list):
            for i in data:
                try:
                    dest_data = json.dumps(i)
                except Exception, e:
                    log.logger.exception("send kafka error: %s" % e)
                    continue
                self.producer.send(self.topic, i)

            return True


    def close(self):
        """
        """
        self.producer.flush()
        self.producer.close()


# class DataQueuePipeline(object):
#     """
#     操作data_queue的对象
#     """
#     def __init__(self, uri):
#         """
#         """
#         import data_queue
#
#         url = urlparse.urlparse(uri)
#         host = url.hostname
#         port = url.port or 27017
#         try:
#             path = url.path.strip('/')
#             i = path.index('.')
#         except Exception:
#             self.db = path
#         else:
#             self.db = path[:i]
#             self.collection = path[i+1:]
#             print(self.db, self.collection)
#
#         try:
#             self.data_queue_sender =  data_queue.Deliver(data_queue.opt.PUSH)
#             self.data_queue_sender.connect(host, port)
#         except Exception as e:
#             log.logger.error("init data_queue_sender failed: %s"%e)
#             raise e
#         #print host, port
#
#     def send(self, data, dest_json=False):
#         """
#         """
#         if self.db and self.collection:
#             return self.data_queue_sender.send({'db':self.db,
#                                                  'collection':self.collection,
#                                                  'data':data})
#         else:
#             return self.data_queue_sender.send(data)
#
#     def close(self):
#         """
#         """
#         self.data_queue_sender.close()


def static_data(data):
    """
    每个配置入库量统计
    :param data: 入库数据
    :return: None
    """

    try:
        # 硬编码
        static_conn = redis.StrictRedis.from_url('redis://192.168.187.13/14')
        config_id = data.get('config_id')
        url = data.get('url')
        if url:
            static_conn.hset("hash_url_gtime_wdc", url, time.time())
        date_str = datetime.datetime.now().strftime("%Y_%m_%d")
        static_key = "hash_config_data_static"
        pipe = static_conn.pipeline()
        # 每日统计key
        key = "{}_{}".format(config_id, date_str)
        # 总计key
        total_key = "{}_{}".format(config_id, 'total')
        pipe.hincrby(static_key, key)
        pipe.hincrby(static_key, total_key)
        pipe.execute()
    except Exception as e:
        log.logger.error("统计出现错误：{}".format(e))


# TODO 增加JS解释器
class JS_execute:
    def __init__(self, **kwargs):
        pass


def dt_parse(data, language="", tzinfo="", country="", fuzzy=True):
    api_url = "http://spider-traefik.istarshine.net.cn:30080/dtxg/dt_parse?"
    # params = "data={}&language={}&tzinfo={}&country={}&fuzzy={}".format(data, language, tzinfo, country, fuzzy)
    params = urlencode({'data': data, "language": language, "tzinfo": tzinfo, "country": country, "fuzzy": fuzzy})
    api_result = requests.get(api_url+params).json()
    if api_result:
        api_result = datetime.datetime.fromtimestamp(api_result.get('result'))
        return api_result
    else:
        log.logger.error("解析时间失败")
        log.logger.error(api_result.get("error_msg"))
    return None


class UtcTime:
    def __init__(self, language="", country=""):
        self.language = language
        self.country = country

    def parse(self, data, fuzzy=True):
        return utc_parse(data, language=self.language, country=self.country, fuzzy=fuzzy)


def utc_parse(data, language="",  country="", fuzzy=True):
    api_url = "http://spider-traefik.istarshine.net.cn:30080/dtxg/utc_parse?"
    # params = "data={}&language={}&country={}&fuzzy={}".format(data, language,  country, fuzzy)
    params = urlencode({'data': data, "language": language, "country": country,  "fuzzy": fuzzy})
    api_result = requests.get(api_url+params).json()
    if api_result:
        api_result = datetime.datetime.fromtimestamp(api_result.get('result'))
        return api_result
    else:
        log.logger.error("解析utc时间失败")
        log.logger.error(api_result.get("error_msg"))
    return None


if __name__ == "__main__":
    pass
#     print is_re_match("aa", "oooooo")
#     print TimeDeltaYears(1)
#     uri = "mongodb://192.168.110.9/data.ba_names"
#     sender = from_uri(uri)
#     data = {'url':'pangwei', 'status':1}
#     res = sender.send(data)
#     sender.close()
#     print res

    #redis
#     uri = 'redis://192.168.100.15/4/data'
#     sender = from_url(uri)
#     import time
#     start = time.time()
#     data = {
#             'title':'title',
#             'content':'content',
#             'url':'http//www.python.org/p/123456',
#             'ctime':datetime.datetime(2014,8,14,01, 01),
#             'gtime':datetime.datetime(2014,8,14,06, 18),
#             'source':'pw',
#             'info_flag':'02',
#             'siteName':'hello'
#             }
# #     for i in xrange(10000):
# #         res = sender.send({'id':i})
#     res = sender.send(data)
#     sender.close()
#     print res
#     print "costs : ", time.time() - start

    #data queue
#     uri = "zmq://192.168.110.10:45000/data.ba_names"
#     try:
#         sender = from_uri(uri)
#         res = sender.send({'url':'pangwei', 'ctime':datetime.datetime.utcnow()})
#     except Exception as e:
#         print e
#     else:
#         sender.close()
#     print res
    
#     uri = 'redis://redis-dupurl-1.istarshine.net.cn/8'
#     save_log(uri, '345', {'config_id':345})
#     mid = '3743906829572599'
#     key = mid_to_url(mid)
#     print "key: ", key
    print url_to_mid('F4nV0euD8')

#     url = 'http://www.baidu.com/p?c=3&a=1####0_1'
#     print canonicalize_url(url)
    
#     print get_verify_code('d:\\temp\\genimg.jpg', 62, 'kronus', 'zhxg130809')
    
#     print os.path.abspath(sys.path[0])
#     resp = get_proxy_by_adsl(6, 1)
#     proxy = resp
#     if proxy:
#         print "---: ", proxy, type(proxy), json.loads(proxy)
#     else:
#         print "--not proxy"

    # t = time.time()
    # print '--start .....'
    #print  scp_img("E:\\eclipse\\spider\\spider\\success_img\\1.jpg")
    # print '---stop .... , total costs:', time.time() - t

    #date_str_list = [
        
        #"2013年8月15日 22:46:21",
        #"2013-11-11 13:52:35",
        #"2013/11/11 13:52:35",
        
        #"2013年8月15日 22:46",
        #"2013-11-11 13:52",
        #"2013/11/11 13:52",
        
        #"2014年5月11日",
        #"2013-11-11",
        #"2013/11/11",
    
        #"2014年5月",
        
        #"13年8月15日 22:46:21",
        #"13年8月15日 22:46",
        
        #"8月15日 22:46:21",
        #"01-03 11:16:21",
        
        #"8月15日 22:46",
        #"01-03 11:16",
    
        #"7/3",
        #"5月11日",
    
    
        
        
        #"3 秒前",
        #"29 分钟前",
        #"2 小时前",
        #"2天前",
        
        #"今天 15:42:21",
        #"昨天 15:42:21",
        #"前天 10:41:21",
        #"今天 15:42",
        #"昨天 15:42",
        #"前天 10:41",
        
        #]
    #for date_str in date_str_list:
        #s = "%s\t%s"%(date_str, util.utc_datetime(date_str))
        #print(s.decode('utf8'))    
        
    #print utc_datetime("2小时前")
