#encoding=utf-8
import logging.config
import ConfigParser
import os,sys

def get_current_path():
    return os.path.dirname(__file__)

logger = logging.getLogger()

log_path = get_current_path() +"/log/"
            
if os.path.isdir(log_path) == False:
    os.makedirs(get_current_path() +"/log/")
    
fp = logging.handlers.RotatingFileHandler(log_path+"clean_dedup.log", maxBytes=100*1024*1024,  mode='a', backupCount=20) 
logger.addHandler(fp)

std = logging.StreamHandler(sys.stderr)
logger.addHandler(std)

formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(filename)s] [%(lineno)d] - %(message)s")
fp.setFormatter(formatter)
std.setFormatter(formatter)

logger.setLevel(logging.NOTSET)


