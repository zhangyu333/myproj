
���ģ�飺athena/utils/data_buffer, ʹ�÷�����
import data_buffer

result = data_buffer.create("redis://192.168.100.14/0/key_name")

data = {}
data["url"]="http://www.example.com"
try:
	result.push(data) #������󣬻�pickleΪ�ַ���
except Exception, e:
	print "exception:%s"%e

������pushall()����������һ�ο��Է������