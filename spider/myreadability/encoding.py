#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
文件名：encoding.py
功能：分析文本编码

代码历史：
2014-12-03：庞 威，创建代码
'''

import re
import chardet

def get_encoding(page):
    # Regex for XML and HTML Meta charset declaration
    charset_re = re.compile(r'<meta.*?charset=["\']*(.+?)["\'>]', flags=re.I)
    pragma_re = re.compile(r'<meta.*?content=["\']*;?charset=(.+?)["\'>]', flags=re.I)
    xml_re = re.compile(r'^<\?xml.*?encoding=["\']*(.+?)["\'>]')

    declared_encodings = (charset_re.findall(page) +
            pragma_re.findall(page) +
            xml_re.findall(page))

    # Try any declared encodings
    if len(declared_encodings) > 0:
        for declared_encoding in declared_encodings:
            #pangwei add on 2015-12-16 begin
            return custom_decode(declared_encoding)
            #pangwei add on 2015-12-16 end
            try:
                page.decode(custom_decode(declared_encoding))
                return custom_decode(declared_encoding)
            except UnicodeDecodeError, e:
                pass

    # Fallback to chardet if declared encodings fail
    text = re.sub('</?[^>]*>\s*', ' ', page)
    encoding = 'utf-8'
    if not text.strip() or len(text) < 10:
        return encoding # can't guess
    res = chardet.detect(text)
    encoding = res['encoding']
    encoding = custom_decode(encoding)
    return encoding

def custom_decode(encoding):
    """Overrides encoding when charset declaration
       or charset determination is a subset of a larger
       charset.  Created because of issues with Chinese websites"""
    try:
        encoding = encoding.lower()
        alternates = {
            'big5': 'big5hkscs',
            'gb2312': 'gbk',
            'ascii': 'utf-8',
            'MacCyrillic': 'cp1251',
            'gbk2312':'gbk'
        }
        if encoding in alternates:
            return alternates[encoding]
        else:
            return encoding
    except:
        return None

if __name__ == '__main__':
    import requests
    
    url = 'http://hkstock.cnfol.com/gangguzixun/20131230/16609624.shtml'
    url = 'http://tieba.baidu.com/p/3446306916'
    url = 'http://news.chinabyte.com/188/13642188.shtml'
    url = 'http://www.smxdaily.com.cn/html/show/cc948806-769c-4109-874f-9c189343c2cf.html'

    resp = requests.get(url)
    encoding = get_encoding(resp.content)
    print "--encoding: ", encoding
    