#coding=utf-8


"""
文件名:util.py
功能:
    url去重工具函数
    
代码历史:
    2014-2-25 : 实现代码
"""

from w3lib.url import *
from urllib2 import urlparse
import urllib
try:
    import cPickle as picklew
except ImportError:
    import pickle
import zlib
import cgi
import hashlib

def unicode_to_str(text, encoding=None, errors='strict'):
    if encoding is None:
        encoding = 'utf-8'
    if isinstance(text, unicode):
        return text.encode(encoding, errors)
    return text

def _parse_url(url, encoding = None):
    return url if isinstance(url, urlparse.ParseResult) else \
        urlparse.urlparse(unicode_to_str(url, encoding))
        
def _unquotepath(path):
    for reserved in ('2f', '2F', '3f', '3F'):
        path = path.replace('%' + reserved, '%25' + reserved.upper())
    return urllib.unquote(path)


def canonicalize_url(url, keep_blank_values = True, keep_fragments = True,
        encoding=None):
    """
    解析url去除无效参数
    """
    scheme, netloc, path, params, query, fragment = _parse_url(url)
    keyvals = cgi.parse_qsl(query, keep_blank_values)
    keyvals.sort()
    query = urllib.urlencode(keyvals)
    path = safe_url_string(_unquotepath(path)) or '/'
    fragment = '' if not keep_fragments else fragment
    
    new_url = urlparse.urlunparse((scheme, netloc.lower(), path, params, query, fragment)) 
    if url[-1:] == "#":
        if new_url[-1] != "#":
            new_url += "#"
    return new_url

def hash_url(url):
    url = canonicalize_url(url)
    sha1 = hashlib.sha1()
    sha1.update(url)
    return sha1.hexdigest()


if __name__ == "__main__":
    url = "http://www.sina.com/1.html?b=3&a=1##"
    print canonicalize_url(url)
