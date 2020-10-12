#coding:utf8
"""
爬虫版本号文件
版本号被改变后 爬虫将自动重启
"""

__version__ = "1.0.15"

# 强制重启子进程接口
force_restart = 0

# 版本说明
# 取消kafka日志记录  好像影响性能。。。
# 配置文件连续空行删除
# 修复追加字段逻辑错误
# 增加 config_info 字段 传递配置文件信息
# 修复url格式错误时统计代码异常
# 增加强制重启接口 应对未知原因造成的子进程卡死
# run.py 增加延迟下载功能

