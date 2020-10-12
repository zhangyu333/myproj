#encoding=utf-8
import logging.config
import ConfigParser
import os,sys

def get_current_path():
    return os.path.dirname(__file__)

logger = logging.getLogger("data_buffer")

log_path = get_current_path() +"/log/"

if os.path.isdir(log_path) == False:
    os.makedirs(get_current_path() +"/log/")

fp = logging.handlers.RotatingFileHandler(log_path+"data_buffer.log", maxBytes=100*1024*1024,  mode='a', backupCount=100)
logger.addHandler(fp)

formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(filename)s] [%(lineno)d] - %(message)s")
fp.setFormatter(formatter)

logger.setLevel(logging.DEBUG)
logging.CRITICAL
#如要关闭， 设置为logging.CRITICAL
#logger.setLevel(logging.CRITICAL)


