#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
文件名：htmlparer.py
功能：生成element tree 分析文本编码

代码历史：
'''


import lxml.html

from encoding import get_encoding

default_parser = lxml.html.HTMLParser(remove_comments=True)

def build_doc(page):
    if isinstance(page, unicode):
        encoding = None
        page_unicode = page
    else:
        try:
            encoding = get_encoding(page) or 'utf8'
        except:
            encoding = 'utf8'
        page_unicode = page.decode(encoding, 'ignore')
    
    doc = lxml.html.document_fromstring(page_unicode, parser=default_parser)
    
    return doc, encoding

def to_string(elem):
    return lxml.html.tostring(elem, encoding='utf8', method='text').strip()