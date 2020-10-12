
入库模块：athena/utils/data_buffer, 使用方法：
import data_buffer

result = data_buffer.create("redis://192.168.100.14/0/key_name")

data = {}
data["url"]="http://www.example.com"
try:
	result.push(data) #任意对象，会pickle为字符串
except Exception, e:
	print "exception:%s"%e

建议用pushall()方法，这样一次可以放入多条