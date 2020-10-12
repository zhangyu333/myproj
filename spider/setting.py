#encoding=utf8

#############################################################################


'''
文件名：setting.py
功能：爬虫多线程运行配置文件；从配置文件spider.cfg读取配置选项和值

代码历史：
'''
import os
import random
import ConfigParser


config = ConfigParser.ConfigParser()
conf_file = os.path.join(os.path.dirname(__file__), 'spider.conf')
config.read(conf_file)

#for section in config.sections():
#    globals().update(config.items())

#threading
PROCESS_NUM = config.getint('threading', 'process_num')
CRAWLER_MODE = config.get('threading', 'crawler_mode')
LIST_PAGE_THREAD_NUM = config.getint('threading', 'list_page_thread_num')
DETAIL_PAGE_THREAD_NUM = config.getint('threading', 'detail_page_thread_num')
DATA_QUEUE_THREAD_NUM = config.getint('threading', 'data_queue_thread_num')
try:
    RESTART_TIME = config.get("threading", "restart_time")
except:
    _hour = random.choice([5, 6, 7] + [12, 13, 14] + [17, 18] + [23, 0, 1])
    _minute = random.choice(range(60))
    RESTART_TIME = "%s:%s" % (_hour, _minute)
    config.set("threading", "restart_time", RESTART_TIME)
    with open(conf_file, "w") as f:
        config.write(f)

#http
try:
    PROXY_ENABLE = config.getboolean('http', 'proxy_enable')
except ValueError:
    PROXY_ENABLE = config.get('http', 'proxy_enable')
PROXY_MAX_NUM = config.getint('http', 'proxy_max_num')
PROXY_AVAILABLE = config.getint('http', 'available_proxy_num')
PROXY_URL = config.get('http', 'proxy_url')
USER_AGENT = config.get('http', 'user_agent')
COMPRESSION = config.getboolean('http', 'compression')
HTTP_TIMEOUT = config.getint('http', 'http_timeout')
COOKIE_ENABLE = config.getboolean('http', 'cookie_enable')
#duanyifei add begin on 2016-03-21
try:
    PROXY_UPDATE_INTERVAL = config.getint('http', 'proxy_update_interval')
except:
    PROXY_UPDATE_INTERVAL = 300
#duanyifei add end on 2016-03-21

#spider
SPIDER_ID = config.get('spider', 'spider_id')
EXIT_TIMEOUT = config.getint('spider', 'exit_timeout')
LIST_DETAIL_INTERVAL = config.getint('spider', 'list_detail_interval')
DATA_ENCODING = config.get('spider', 'data_encoding')
REPEAT_TIMES = config.getint('spider', 'repeat_times')
SHOW_DATA = config.getboolean('spider', 'show_data')
try:
    ADSL_ID = config.getint('spider', 'adsl_id')
except:
    ADSL_ID = -1

#duanyifei add begin on 2016-05-25
try:
    CONFIG_MONITOR= config.getboolean('spider', 'config_monitor')
except:
    CONFIG_MONITOR = False
#duanyifei add end on 2016-05-25

# dispatch
DEFAULT_DISPATCH_HOST = os.getenv("dispatch_host", "").strip()
# 爬虫分类参数
SPIDER_TYPE = os.getenv("spider_type", "spider")
# 兼容旧配置文件
if config.has_option("spider", "dispatch_host"):
    if not DEFAULT_DISPATCH_HOST:
        DEFAULT_DISPATCH_HOST = config.get("spider", "dispatch_host")
    GET_SPIDER_CONFIG_FROM = config.get('spider', 'get_spider_config_from').format(DEFAULT_DISPATCH_HOST)
    ADD_SPIDER_FROM = config.get('spider', 'add_spider_from').format(DEFAULT_DISPATCH_HOST, SPIDER_TYPE)
    SPIDER_HEARTBEAT_FROM = config.get('spider', 'spider_heartbeat_from').format(DEFAULT_DISPATCH_HOST)
    SEND_CRAWL_RESULT_TO = config.get('spider', 'send_crawl_result_to').format(DEFAULT_DISPATCH_HOST)
    GET_SPIDER_PARAM_FROM = config.get('spider', 'get_spider_param_from').format(DEFAULT_DISPATCH_HOST)
    GET_CONFIG_CONTENT_FROM = config.get('spider', 'get_config_content_from').format(DEFAULT_DISPATCH_HOST)
else:
    GET_SPIDER_CONFIG_FROM = config.get('spider', 'get_spider_config_from')
    ADD_SPIDER_FROM = ''
    SPIDER_HEARTBEAT_FROM = ''
    SEND_CRAWL_RESULT_TO = config.get('spider', 'send_crawl_result_to')
    GET_SPIDER_PARAM_FROM = config.get('spider', 'get_spider_param_from')
    GET_CONFIG_CONTENT_FROM = ""

#dedup
DEDUP_URI = config.get('dedup', 'dedup_uri')
DEDUP_KEY = config.get('dedup', 'dedup_key')


#daemon_app
STDIN_PATH = config.get('daemon_app', 'stdin_path')
STDOUT_PATH = config.get('daemon_app', 'stdout_path')
STDERR_PATH = config.get('daemon_app', 'stderr_path')
PIDFILE_PATH = config.get('daemon_app', 'pidfile_path')
PIDFILE_TIMEOUT = config.getint('daemon_app', 'pidfile_timeout')


#data_queue
SPIDER_DATA_DB = config.get('data_db', 'spider_data_db')
SPIDER_LOG_DB = config.get('data_db', 'spider_log_db')
CRAWLER_LIST_DATA = config.get('data_db', 'crawler_list_data')

#pangwei add begin on 2016-03-14
import platform

def get_windows_localip():
    import socket
    local_ip = socket.gethostbyname(socket.gethostname())#这个得到本地ip
    return local_ip

def get_linux_localip():
    import socket
    import fcntl
    import struct

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    local_ip  =  socket.inet_ntoa(fcntl.ioctl(s.fileno(),0x8915, struct.pack('256s', "eth0"[:15]))[20:24])
    
    return local_ip

def get_localip():
    local_ip = ""
    try:
        if  platform.system() == "Windows":
            local_ip =  get_windows_localip()
        else:
            local_ip =  get_linux_localip()
    except Exception, e:
        local_ip = ""
    return local_ip

SPIDER_IP = get_localip()

#pangwei add end on 2016-03-14

if __name__ == "__main__":
    setting_keys = []
    for key, value in locals().items():
        if key.replace("_", "").isupper():
            setting_keys.append((key, value))

    setting_keys.sort(key=lambda x: x[0])
    for key, value in setting_keys:
        print("%s\t%s\t%s \n" % (key, type(value), repr(value)))
