# Embedded file name: /work/build/source/athena/utils/data_buffer/test.py
import data_buffer
result = data_buffer.create('redis://192.168.174.140/3/data_tmp')

#192.168.174.140/3/data_tmp
data = result.pop()
result.push(data)
print data
print data['url']
print data['title']
print data['ctime']
print data['gtime']
print data['siteName']
print data['content']

import ujson as json

a = json.dumps(data)
print a
