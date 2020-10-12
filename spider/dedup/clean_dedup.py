#coding:utf-8

import time

import redis


def clean_dedup(con_str, key, score):
    db = redis.StrictRedis.from_url("redis://%s"%(con_str))
    try:
        count = db.zremrangebyscore(key, 0, time.time() - score)
    except:
        count = 0
    return count



dedups = [
    ["192.168.110.46:6379/0", "tieba_dedup", 10 * 24 * 3600],
    ["192.168.110.46:6379/1", "sina_dedup",  10 * 24 * 3600],
    ["192.168.110.46:6379/1", "qq_dedup",  10 * 24 * 3600],
    ["192.168.110.40:6379/0","dedup",  10 * 24 * 3600],
    ["192.168.110.40:6379/1", "dedup2", 10 * 24 * 3600],
    ["192.168.110.48:6379/0", "tieba_filter", 10 * 24 * 3600],
    ["192.168.110.48:6379/0","filter", 10 * 24 * 3600],
    ["192.168.110.48:6379/0", "area_dedup", 10 * 24 * 3600]
    ]

def run():
    global dedups
    while 1:
        print "开始清除过期数据"
        for con_str, key, seconds in dedups:
            try:
                count = clean_dedup(con_str, key, seconds)
                print "con:%s key:%s count:%d"%(con_str, key, count)
            except Exception as e:
                print "con:%s key:%s error:%s"%(con_str, key, e)
        time.sleep(3600)
        

def main():
    run()
    
"""    
def test():
    global dedups
    for con_str, key, seconds in dedups:
        db = redis.from_url(con_str)
        db.zadd(key, "test1", time.time() - 12 * 24 * 3600)
        db.zadd(key, "test2", time.time() - 11 * 24 * 3600)
        db.zadd(key, "test3", time.time() - 9 * 24 * 3600)
        db.zadd(key, "tet4", time.time() - 1 * 24 * 3600)
        db.zadd(key, "test5", 0)
    run()
"""
    
if __name__ == "__main__":
    run()
    

        



