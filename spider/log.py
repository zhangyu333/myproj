#!/usr/bin/env python
#coding=utf-8

#############################################################################


'''
文件名：setting.py
功能：爬虫多线程运行配置文件；从配置文件spider.cfg读取配置选项和值

代码历史：

'''
import os
import sys
try:
    import ujson as json
except ImportError:
    import json
import time
import logging
import traceback
import logging.handlers
from multiprocessing import Lock

try:
    import setting
    spider_id = setting.SPIDER_ID
    spider_ip = setting.SPIDER_IP
except ImportError:
    spider_id = ""
    spider_ip = ""


class SpiderRotatingFileHandler(logging.handlers.RotatingFileHandler):
    '''
    文件回滚日志处理器
    特点:
        1. 利用备份文件修改时间做判断 修复了多进程下同时多个日志文件被写入的bug
        2. 可选项 使用json格式记录日志文件
    
    '''
    def __init__(self, filename, mode='a', maxBytes=0,
                 backupCount=0, encoding=None, delay=0, is_json=False):
        logging.handlers.RotatingFileHandler.__init__(self,
            filename, mode, maxBytes, backupCount, encoding, delay)
        # 格式处理器
        self.Formatter = logging.Formatter()
        # 进程锁
        self.my_lock = Lock()

        self.is_json = is_json
        if self.is_json:
            self.format = self.json_format

    def json_format(self, record):
        '''
        json 格式化日志
        @record: 日志记录对象
        type: logging.LogRecord
        '''
        # 增加 asctime 属性
        record.asctime = self.Formatter.formatTime(record)
        #
        message = record.getMessage()
        log_data = {}
        # 检查是否为json格式 并且是字典形式
        try:
            log_data = json.loads(message)
            if not isinstance(log_data, dict):
                log_data = {}
        except Exception as e:
            exc_info = traceback.format_exc()
            #sys.stderr.write(exc_info)

        if not log_data:
            log_data.update({
                "_message": message,
                })
        
        # 增加爬虫信息
        log_data.update({
            "spider_id": spider_id,
            "spider_ip": spider_ip,
            })
        
        # 获取日志基本信息
        log_record_basic_fields = [
            "levelname", "filename", "lineno",
            "name", "created", "asctime", "process",
        ]        
        
        for attr in log_record_basic_fields:
            value = getattr(record, attr, "")
            log_data.update({
                "_{}".format(attr): value,
                })
        try:
            result = json.dumps(log_data, ensure_ascii=False)
        except:
            result = json.dumps(log_data)
        return result

    def doRollover(self):
        """
        Do a rollover, as described in __init__().
        """
        with self.my_lock:
            if self.stream:
                self.stream.close()
                self.stream = None
            lock_file = "%s.lock"%self.baseFilename
            max_modify_interval = 3 # seconds
            do_flag = 0
            
            # 利用 Lock 文件被修改时间保证不会出现同时多个文件被写入
            if not os.path.exists(lock_file):
                with open(lock_file, "w"):
                    pass
                do_flag = 1
            elif time.time() - os.stat(lock_file).st_mtime > max_modify_interval:
                do_flag = 1
            else:
                pass
            if do_flag:
                for i in range(self.backupCount - 1, 0, -1):
                    sfn = "%s.%d" % (self.baseFilename, i)
                    dfn = "%s.%d" % (self.baseFilename, i + 1)
                    if os.path.exists(sfn):
                        # 删除最大备份文件
                        if os.path.exists(dfn):
                            os.remove(dfn)
                        os.rename(sfn, dfn)
                        
                dfn = self.baseFilename + ".1"
                if os.path.exists(dfn):
                    os.remove(dfn)
                    
                if os.path.exists(self.baseFilename):
                    os.rename(self.baseFilename, dfn)
                # 刷新 Lock 文件修改时间
                with open(lock_file, "w"):
                    pass

        if not self.delay:
            self.stream = self._open()
        return


def make_dispatch_log(exc_text="", code=0, extra={}):
    '''调度日志生成
    @error: 失败原因
    @code: 0(成功) or other ..
    '''
    _log = {
        "exc_text": exc_text,
        "code": code,
        "kafka_topic": "spider_dispatch",
        }
    if extra:
        _log.update(extra)
        if code == 0:
            # 成功时不记录内容
            _log.pop("config_content", "")
    return json.dumps(_log)


def make_config_log(exc_text="", config_id=-1, extra={}):
    '''调度日志生成
    @error: 失败原因
    @code: 0(成功) or other ..
    '''
    if not config_id:
        config_id = -1
    _log = {
        "kafka_topic": "spider_config",
        "config_id": config_id,
        "exc_text": exc_text,
        }
    if extra:
        _log.update(extra)
    return json.dumps(_log)

def make_spidercode_log(exc_text="", config_id=-1, extra={}):
    '''调度日志生成
    @error: 失败原因
    @code: 0(成功) or other ..
    '''
    if not config_id:
        config_id = -1
    _log = {
        "kafka_topic": "spider_code",
        "config_id": config_id,
        "exc_text": exc_text,
        }
    if extra:
        _log.update(extra)
    return json.dumps(_log)


logger = logging.getLogger()

current_file_path = os.path.dirname(os.path.abspath(sys.path[0]))
log_path = os.path.join(current_file_path, "log")

if not os.path.isdir(log_path):
    os.makedirs(log_path)

# 本地日志文件
fp = SpiderRotatingFileHandler(os.path.join(log_path, "debug.log"), maxBytes=10*1024*1024,  mode='a', backupCount=10)
logger.addHandler(fp)

# 标准输出流
std = logging.StreamHandler(sys.stdout)
logger.addHandler(std)

# json格式文件 为kafka定制
sfp = SpiderRotatingFileHandler(os.path.join(log_path, "bak.log"), maxBytes=2*1024*1024, backupCount=2, is_json=True)
# 不启用
# logger.addHandler(sfp)

# 定制标准输出和本地文件日志格式
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(filename)s] [%(lineno)d] - %(message)s")
fp.setFormatter(formatter)
std.setFormatter(formatter)


# 守护进程中保留的文件描述符
daemon_files_preserve = [fp.stream, sfp.stream, std.stream]


logger.setLevel(logging.NOTSET)
#logger.setLevel(logging.ERROR)


if __name__ == "__main__":
    logger.debug("hello")
