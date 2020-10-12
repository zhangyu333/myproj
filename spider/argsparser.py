#!/usr/bin/env python
#coding:utf-8

#############################################################################


'''
文件名：argparser.py
功能：

代码历史：
2014-05-12：庞 威，创建代码
'''
import argparse

class Args(object):
    pass

parser = argparse.ArgumentParser()

def cmd_parse():
    """
    """
    group_spider = parser.add_argument_group("spider", u"spider 配置参数")
    group_spider.add_argument("--spider_id", nargs='?', dest="SPIDER_ID", help=u"设置当前爬虫id")
    group_spider.add_argument("--config", nargs='?', dest="GET_SPIDER_CONFIG_FROM", help=u"爬虫配置文件", metavar="config.py")
    group_spider.add_argument("--param", nargs='?', dest="GET_SPIDER_PARAM_FROM", help=u"获取协作数据服务器地址")
    group_spider.add_argument("--result", nargs='?', dest="SEND_CRAWL_RESULT_TO", help=u"爬虫统计结果返回地址")
    
    group_http = parser.add_argument_group("http", u"http 配置参数")
    group_http.add_argument("--proxy", action="store_true", dest="PROXY_ENABLE", default='', help=u"下载时使用代理; 默认为真.")
    group_http.add_argument("--proxy_disable", action="store_false", dest="PROXY_ENABLE", help=u"下载时不使用代理;")
    group_http.add_argument("--cookie", action="store_true", dest="COOKIE_ENABLE", default=None, help=u"下载时使用cookie;")
    group_http.add_argument("--cookie_disable", action="store_false", dest="COOKIE_ENABLE", default=None, help=u"下载时不使用代理;")
    group_http.add_argument("--proxy_url", nargs='?', dest="PROXY_URL", help=u"代理文件地址")
    group_http.add_argument("--proxy_max", nargs='?', dest="PROXY_MAX_NUM", type=int, help=u"同一代理最大连续使用次数")
    group_http.add_argument("--timeout", nargs='?', dest="HTTP_TIMEOUT", type=int, help=u"http超时时间")
    group_http.add_argument("--user_agent", nargs='?', dest="user_agent", help=u"下载时使用的user-agent")
    
    group_threading = parser.add_argument_group("threading", u"threading 配置参数")
    group_threading.add_argument("--mode",  dest="CRAWLER_MODE", choices=("threading", "gevent"), default=None, help=u"爬虫运行方式; 默认为threading.")
#    group_threading.add_argument("--gevent", action="store_false", dest="crawler_mode", default=True, help=u"以gevent方式执行")
    group_threading.add_argument("--list_num", dest="LIST_PAGE_THREAD_NUM", type=int, nargs='?', help=u"列表页线程数目")
    group_threading.add_argument("--detail_num", dest="DETAIL_PAGE_THREAD_NUM", type=int, nargs='?', help=u"详情页线程数目")
    
    group_db = parser.add_argument_group("db", u"db 配置参数")
    group_db.add_argument("--db", dest="CRAWLER_DATA", nargs='?', help=u"抓取数据存放地址")
    group_db.add_argument("--log_db", dest="SPIDER_LOG", nargs='?', help=u"爬虫日志存放地址")
    
    group_daemon = parser.add_argument_group("daemon", u"daemon 配置参数")
    group_daemon.add_argument("--pidfile_path", nargs='?', dest="pidfile_path", help=u"保存进程id的文件路径")
#     group_daemon.add_argument("--start", action="store_false", dest="daemon_run", default=False, help=u"以守护进程方式开始运行")
#     group_daemon.add_argument("--stop", action="store_false", dest="daemon_run", default=False, help=u"结束爬虫进程")


    group = parser.add_mutually_exclusive_group()
    group.add_argument('--debug', action='store_true', default=None, help=u"调试模式运行")
    group.add_argument('--start', action='store_true', default=None, help=u"以守护进程方式开始运行")
    group.add_argument("--stop", action='store_true',  default=None, help=u"结束爬虫进程")

    group_log_level = parser.add_argument_group("log_level", u"日志级别参数")
    group_log_level.add_argument("--log_level", nargs='?', help=u"日志级别")
    
    cmd_args = parser.parse_args()
    
    return cmd_args

def print_usage():
    return parser.print_usage()

if __name__ == "__main__":
    args = cmd_parse()
    print args
    print print_usage()
#    print args.__dict__['PROXY_ENABLE']
