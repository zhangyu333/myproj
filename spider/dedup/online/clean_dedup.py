#coding:utf-8

import time

import redis
import log

def clean_dedup(con_str, key, score):
    db = redis.StrictRedis.from_url("redis://%s"%(con_str))
    
    log.logger.info("删除:%s, %s, %s天之前"%(con_str, key, score/(3600*24)))
    try:
        count = db.zremrangebyscore(key, 0, time.time() - score)
    except:
        count = 0
    return count



dedups = [
    ["redis-dupurl-1.istarshine.net.cn:6379/0", "tieba_dedup", 3 * 24 * 3600],
    ["redis-dupweibo-1.istarshine.net.cn:6379/0", "qq_dedup",  3 * 24 * 3600],
    ["redis-dupurl-1.istarshine.net.cn:6379/0","dedup",  5 * 24 * 3600],
    ["redis-dupurl-1.istarshine.net.cn:6379/0", "local_dedup", 5 * 24 * 3600],
    ["redis-dupweibo-1.istarshine.net.cn:6379/0", "sina_dedup",  3 * 24 * 3600],
    ["redis-collectioncache-1.istarshine.net.cn:6379/0", "overseas_router", 5 * 24 * 3600],
    ["redis-collectioncache-1.istarshine.net.cn:6379/0", "tieba_filter", 5 * 24 * 3600],
    ["redis-collectioncache-1.istarshine.net.cn:6379/0","filter", 5 * 24 * 3600],
    ["redis-collectioncache-1.istarshine.net.cn:6379/0", "local_filter", 5 * 24 * 3600],
    ["redis-collectioncache-1.istarshine.net.cn:6379/0", "overseas_filter", 5 * 24 * 3600],
    ["redis-collectioncache-1.istarshine.net.cn:6379/0", "dedup_topic", 3 * 3600],
    ["redis-collectioncache-1.istarshine.net.cn:6379/0", "filter_topic", 3 * 3600]
    ]

def run():
    global dedups
    
    log.logger.info( "开始清除过期数据....." )
    s_t = time.time()
    total_count = 0
    for con_str, key, seconds in dedups:
        try:
            t1 = time.time()
            log.logger.info("开始清除:%s, %s"%(con_str, key))
            count = clean_dedup(con_str, key, seconds)
            total_count += count
            delta_t = time.time() - t1
            log.logger.info( "清除结束：con:%s key:%s count:%d，耗时:%f 秒"%(con_str, key, count, delta_t))
        except Exception as e:
            log.logger.exception("异常:%s, con:%s key:%s"(e, con_str, key) )
    e_t = time.time()
    log.logger.info("清除完毕，清除key %d, url总数：%d, 耗时:%f 秒"%(len(dedups), total_count, e_t - s_t))

def clean_by_days(con_str, key, days):
    log.logger.info( "开始清除过期数据....." )
    s_t = time.time()
    total_count = 0
    
    for i in range(days, 0, -1):
        try:
            t1 = time.time()
            log.logger.info("开始清除:%s, %s， 第%d 天前"%(con_str, key, i))
            seconds = i*3600*24
            count = clean_dedup(con_str, key, seconds)
            total_count += count
            delta_t = time.time() - t1
            log.logger.info( "清除结束：con:%s key:%s count:%d，耗时:%f 秒"%(con_str, key, count, delta_t))
            if count>0:
                break
        except Exception as e:
            log.logger.exception("异常:%s, con:%s key:%s"(e, con_str, key) )
            
    e_t = time.time()
    log.logger.info("清除完毕，清除key %d, url总数：%d, 耗时:%f 秒"%(len(dedups), total_count, e_t - s_t))
        
    
if __name__ == "__main__":
    #run()
    clean_by_days("redis-dupweibo-1.istarshine.net.cn:6379/0", "sina_dedup", 100)
