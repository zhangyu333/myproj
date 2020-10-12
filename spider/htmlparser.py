#!/usr/bin/env python
# coding:utf-8

"""
代码历史：
2019-06-27: 优化xpathall性能, 增加remove_tree方法,微调其他各处;
            旧Parser类存在Parser.data和Parser._root结构或内容不一致的情况, 为了保证旧配置正常运行, 暂不处理.
2020/9/29: 优化htmlparser，python3与python2兼容
"""

import re
import time
import datetime
import urlparse
import urllib
from lxml import etree
from lxml.html import html_parser
import log
import util


_DOT = u"."
bad_attrs = ['width', 'height', 'style', '[-a-z]*color', 'background[-a-z]*', 'on*']
single_quoted = "'[^']+'"
double_quoted = '"[^"]+"'
non_space = '[^ "\'>]+'
htmlstrip = re.compile("<"  # open
                       "([^>]+) "  # prefix
                       "(?:%s) *" % ('|'.join(bad_attrs),) +  # undesirable attributes
                       '= *(?:%s|%s|%s)' % (non_space, single_quoted, double_quoted) +  # value
                       "([^>]*)"  # postfix
                       ">"  # end
                       , re.I)


def clean_attributes(html):
    while htmlstrip.search(html):
        html = htmlstrip.sub('<\\1\\2>', html)
    return html


# def timer(func):
#     """计算func运行耗时, 用于测试"""
#     def inner(*args, **kwargs):
#         start = time.time()
#         result = func(*args, **kwargs)
#         cost = time.time() - start
#         log.logger.debug("{} costs {:.6f} sec".format(func.__name__, cost))
#         return result
#     return inner


class Parser(object):
    
    _compat_pattern_1 = re.compile(r"(?u)\|\s*/")
    _compat_pattern_2 = re.compile(r"(?u)\(\s*/")
    
    def __init__(self, data=None, url="", encoding="utf8", response=None, clean=False, **kwargs):
        """
        :param data: <type 'basestring'>
        :param url: <type 'basestring'>
        :param encoding: deprecated, 原用于内部实例化是执行etree._Element序列化编码，新版仅用于data解码
        :param response: <type 'requests.models.Response'>，与data对应的response实例
        :param clean: <type 'bool'>, 清除全部style属性的标志，默认False
        :param kwargs:
            1. root: <type 'etree._Element'>, 可通过root参数传入etree._Element类型，以此构造Parser实例。
                     此参数用于兼容data实例化, 同时在调用xpathall时传递节点引用，避免反复序列化节点树；
        """
        root = kwargs.get("root", None)
        if data is None and root is None:
            raise ValueError("Parser needs either data or root argument")
        
        if not url and response is not None:
            self.m_url = response.request.url.decode('utf-8')
        else:
            self.m_url = url.decode('utf-8') if isinstance(url, str) else url
        self.encoding = encoding
        self.clean = clean
        self.kwargs = kwargs
        self.response = response

        if data is not None:
            assert isinstance(data, basestring), \
                "data should be type 'basestring', but got {}".format(type(data))
            data = data.decode(encoding) if isinstance(data, str) else data
            if root is None:
                data = re.sub("(?u)^<\?(XML|xml)[^>]+>\s*", "", data)
                if clean:
                    data = util.filter_style_script(data)
                root = etree.HTML(data or "<html/>", parser=html_parser)
                if self.m_url:
                    try:
                        root.make_links_absolute(self.m_url, resolve_base_href=True, handle_failures="ignore")
                    except Exception as e:
                        log.logger.warning(util.R("Make links absolute failed: {}".format(e)))
        self._root = root
        self._expr = self.kwargs.get("_expr", _DOT)
        self._data = data
    
    def __str__(self):
        query_path = self._expr.encode("utf-8")
        tag = self._root.tag \
            if not isinstance(self._root, (etree._ElementUnicodeResult, etree._ElementStringResult)) \
            else "text"
        data = "{}...".format(self._data[:15].strip()) if self._data else None
        return "<{cls} xpath={exp} tag={tag}, source_data={data}>".format(cls=self.__class__.__name__, exp=query_path, tag=tag, data=data)
    
    @property
    def data(self):
        """由于历史原因, _data与_root结构不一致的问题暂不处理;
        统一后可能会导致大量配置regex, regexall出现异常(旧版本根据_data进行正则匹配搜索);
        :return: <type 'unicode'>
        """
        if self._data is not None:
            _data = self._data
        else:
            if isinstance(self._root, etree._ElementStringResult):
                _data = str(self._root).decode("utf-8")
            elif isinstance(self._root, etree._ElementUnicodeResult):
                _data = unicode(self._root)
            else:
                _data = etree.tostring(self._root, method="html", encoding="unicode")
        return _data
    
    def _compat_xpath(self, xp):
        """兼容旧Parser类XPath绝对路径，将XPath表达式转换为相对路径;
        同时将xp转为unicode类型, 兼容XPath中存在中文的情况;
        可能的情况:
        //exp[contains(@class, "aaa bbb")]
        // exp[ @id = "jf da" ]
        //exp|//exp|//exp
        (//exp)[0]
        (//exp|//exp)[0]
        .//exp
        //exp
        :param xp: <type 'basestring'>
        :return: <type 'unicode'>
        """
        xp = xp.decode("utf-8") if isinstance(xp, str) else xp
        xp = self._compat_pattern_1.sub("|./", xp)
        xp = self._compat_pattern_2.sub("(./", xp)
        if xp.startswith("/"):
            query = _DOT + xp
        else:
            query = xp
        return query
    
    def xpathall(self, xp):
        """返回Parser实例时通过传递节点引用，避免重复进行序列化和反序列化
        同时为了兼容旧配置，不改变原有配置编写规则，修改xpath为相对路径
        :param xp: <type 'basestring'>
        :return: <type 'list'>
        """
        query = self._compat_xpath(xp)
        try:
            nodes = self._root.xpath(query)
        except Exception as e:
            log.logger.debug(
                util.R(u"异常: xpath错误; Xpath Expression is {expr}, Message: {msg}".format(expr=query, msg=e.message))
            )
            result = list()
        else:
            if nodes:
                result = [self.__class__(root=x, _expr=query) for x in nodes]
            else:
                log.logger.debug(util.BB(u"xpath 解析无结果: {0}; url: {1}".format(query, self.m_url)))
                result = list()
        return result
    
    def __nonzero__(self):
        # todo (lihanxuan) 这里看起来永远都为True, 待分析
        return bool(self.data)
    
    def xpath(self, xp, default=""):
        """
        :param xp: <type 'basestring'>
        :param default: <type 'basestring'>
        :return: <type 'Parser'>
        """
        query = self._compat_xpath(xp)
        try:
            nodes = self._root.xpath(query)
        except Exception as e:
            log.logger.debug(
                util.R(u"异常: xpath错误; Xpath Expression is {expr}, Message: {msg}".format(
                    expr=query, msg=e.message)
                )
            )
            result = self.__class__(data=default)
        else:
            if nodes:
                result = self.__class__(root=nodes[0], _expr=query)
            else:
                log.logger.debug(util.BB(u"xpath 解析无结果: {0}; url: {1}".format(query, self.m_url)))
                result = self.__class__(data=default)
        return result
    
    def regexall(self, reg):
        """
        :param reg: <type 'basestring'>
        :return: <type 'list'>
        """
        unicode_exp = reg.decode("utf-8") if isinstance(reg, str) else reg
        try:
            result_list = re.compile(unicode_exp).findall(self.data)
        except Exception as e:
            log.logger.debug(
                util.R(u"异常：regex 解析错误，reg is {reg}; exception: {e};  url: {url}".format(
                    reg=unicode_exp, e=e.message, url=self.m_url)
                )
            )
            result = list()
        else:
            if result_list:
                result = [self.__class__(data=x) for x in result_list]
            else:
                log.logger.debug(util.BB(u"regexall 解析无结果: {0}; url: {1}".format(unicode_exp, self.m_url)))
                result = list()
        return result
    
    def regex(self, reg, default=""):
        """
        :param reg: <type 'basestring'>
        :param default: <type 'basestring'>
        :return: <type 'Parser'>
        """
        unicode_exp = reg.decode("utf-8") if isinstance(reg, str) else reg
        try:
            result_list = re.compile(unicode_exp).findall(self.data)
        except Exception as e:
            log.logger.debug(
                util.R(u"异常：regex 解析错误，reg is {reg}; exception: {e};  url: {url}".format(
                    reg=unicode_exp, e=e.message, url=self.m_url)
                )
            )
            result = self.__class__(data=default)
        else:
            if result_list:
                result = self.__class__(data=result_list[0])
            else:
                log.logger.debug(util.BB(u"regex 解析无结果: {0}; url: {1}".format(unicode_exp, self.m_url)))
                result = self.__class__(data=default)
        return result
    
    def text(self, encoding="utf-8", with_tail=True):
        """
        :param encoding:
        :param with_tail: <type 'bool'>, True提取时包含tail文本, False只提取text文本
        :return: <type 'str'>
        """
        if isinstance(self._root, etree._ElementStringResult):
            text = str(self._root)
        elif isinstance(self._root, etree._ElementUnicodeResult):
            text = unicode(self._root).encode(encoding)
        else:
            text = etree.tostring(self._root, method="text", encoding=encoding, with_tail=with_tail)
        return text
    
    def remove_tree(self, xp, with_tail=False):
        """移除指定子树，选择是否同时移除tail文本
        :param xp: XPath Expression
        :param with_tail: <type 'bool'>; True同时移除tail文本, False保留tail文本
        :return: <type 'Parser'>
        为兼容clear_special_xp, 便于后续优化, 这里返回原Parser实例, 保证效果和clear_special_xp相似
        """
        query = self._compat_xpath(xp)
        try:
            nodes = self._root.xpath(query)
        except Exception as e:
            log.logger.debug(util.R(u"异常: XPath 错误, xp is {xp}, Exception: {e}".format(
                xp=query, e=e.message))
            )
        else:
            for node in nodes:
                parent = node.getparent()
                assert parent is not None
                if not isinstance(node, etree._Element):
                    log.logger.debug(util.BB(
                        u"remove_tree 提示, {} cannot be removed.".format(type(node))
                    ))
                    continue
                if node.tail and not with_tail:
                    previous = node.getprevious()
                    if previous is None:
                        parent.text = (parent.text or '') + node.tail
                    else:
                        previous.tail = (previous.tail or '') + node.tail
                parent.remove(node)
        return self
    
    def int(self, default=-1):
        data = self.data
        try:
            result = int(data)
        except Exception as e:
            log.logger.debug(u"异常: int转换错误 {0}, data='{1}'".format(e.message, data))
            result = default
        return result
    
    def datetime(self):
        return util.utc_datetime(self.data)
    
    def cssall(self, cssexp):
        css_query = cssexp.decode("utf-8") if isinstance(cssexp, str) else cssexp
        try:
            node_list = self._root.cssselect(css_query)
        except Exception as e:
            log.logger.debug(util.R(u"异常: css 解析错误: css is {0}; exception:{1}; url:{2}".format(css_query, e.message, self.m_url)))
            result = list()
        else:
            if node_list:
                result = [self.__class__(root=x, _expr=css_query) for x in node_list]
            else:
                log.logger.debug(util.BB(u"cssall 解析无结果: {0}; url: {1}".format(css_query, self.m_url)))
                result = list()
        return result
    
    def css(self, cssexp, default=""):
        css_query = cssexp.decode("utf-8") if isinstance(cssexp, str) else cssexp
        try:
            node_list = self._root.cssselect(css_query)
        except Exception as e:
            log.logger.debug(util.R(u"异常: css 解析错误: css is {0}; exception:{1}; url:{2}".format(css_query, e.message, self.m_url)))
            result = self.__class__(data=default)
        else:
            if node_list:
                result = self.__class__(root=node_list[0], _expr=css_query)
            else:
                log.logger.debug(util.BB(u"css 解析无结果: {0}; url: {1}".format(css_query, self.m_url)))
                result = self.__class__(data=default)
        return result
    
    def strip(self):
        data = re.sub(r'(?u)(&#160;)+$', u'', self.data.strip())
        return self.__class__(data=data.strip())
    
    def str(self, encoding="utf8"):
        return self.data.encode(encoding)
    
    def html(self, encoding="utf8"):
        """返回序列化节点树_root"""
        return etree.tostring(self._root, encoding=encoding, method="html")
    
    def cleaned_html(self, encoding="utf-8"):
        return self.html(encoding)
    
    def float(self, default=0.0):
        try:
            result = float(self.data)
        except Exception as e:
            log.logger.debug(u"异常：float转换错误，{0}".format(e.message))
            result = default
        return result

    def url(self, remove_param=False):
        """
        把data转换为标准的url格式，如果url有参数，则按照升序重新排列，防止url相同，但是参数顺序不同而造成的url不同的识别错误，
        例如http://xxx.com/123.html?b=1&a=3，则返回http://xxx.com/123.html?a=3&b=1；
        如果remove_param=True，则删除参数，例如http://xxx.com/123.html?b=1&a=3，则返回为http://xxx.com/123/html；
        如果是相对路径，例如123.html，则返回绝对路径：http://xxx.com/123.html，并识别/123.html,则为http://xxx.com/123.html
        注意：识别url需要在__init__中设置url参数，否则无法识别相对路径的Url
        """
        # todo(lihanxuan) 这里对self.data进行urlsplit操作有疑问，待分析
        uri = urlparse.urlsplit(self.data)
        # 对参数进行排序，名字升序
        query = urlparse.parse_qsl(uri.query, True)
        query.sort()
        query = urllib.urlencode(query)
    
        if uri.netloc == "":
            # 没有域名
            result = urlparse.urljoin(self.m_url,
                                      urlparse.urlunsplit((uri.scheme, uri.netloc, uri.path, query, uri.fragment)))
        else:
            result = urlparse.urlunsplit((uri.scheme, uri.netloc, uri.path, query, uri.fragment))
    
        return result
    
    def replace(self, pattern, repl, count=0):
        """
        将data中满足规则pattern的元素替换为字符串repl;
        参数count表示替换发生的最大次数；必须为非负整数；默认为0,表示替换所有符合条件的元素；
        """
        try:
            result = re.compile(pattern).sub(repl, self.data, count)
        except Exception as e:
            log.logger.debug(u"异常：replace 替换错误，{0}".format(e.message))
            return self
        else:
            return self.__class__(data=result)
    
    def delete(self, pattern, count=0):
        """
        删除data中符合规则pattern的元素；参数count同sub
        """
        try:
            result = re.compile(pattern).sub("", self.data, count)
        except Exception as e:
            log.logger.debug(u"异常：replace 替换错误，{0}".format(e.message))
            return self
        else:
            return self.__class__(data=result)
    
    def urls(self, base_url, domains=None, regex=None):
        """
        找出所有的有效url;
        参数base_url代表url前缀，用来生成绝对url; 参数domains指允许的url域；regex是一个正则表达式，用来过滤url;
        """
        url_set = set(self._root.xpath(".//a/@href|.//iframe/@src"))
        pattern = re.compile(regex, re.U) if regex is not None else None
        urls = list()
        for url in url_set:
            if pattern:
                try:
                    res = pattern.findall(url)
                except Exception as e:
                    log.logger.debug(u"异常：findall in urls() 解析错误， {0}".format(e.message))
                    continue
                else:
                    if res:
                        url = res[0]
            if str(url).startswith("/"):
                if base_url is not None:
                    # todo(lihanxuan) 这里url拼接方式有疑问，待分析
                    url = base_url + url
                    urls.append(url)
                elif self.m_url is not None:
                    # todo(lihanxuan) 这里self.m_url判断条件有疑问，待分析
                    url = self.m_url + url
                    urls.append(url)
                else:
                    continue
            elif url.startswith(("http://", "https://")):
                uri = urlparse.urlsplit(url)
                if domains is not None:
                    if uri.netloc and uri.netloc in domains:
                        urls.append(url)
                else:
                    urls.append(url)
        return urls
    
    def remove(self, xp):
        """Deprecated
        去除指定xpath对应的数据 返回一个不包含已去除数据的
        """
        log.logger.warning(
            "This method will be deprecated in new version, "
            "It is recommended to use 'remove_tree()'."
        )
        query = self._compat_xpath(xp)
        try:
            nodes = self._root.xpath(query)
            for node in nodes:
                node.getparent().remove(node)
        except Exception as e:
            log.logger.debug(util.R(u"异常：xpath 解析错误: xp is {0}; exception:{1}; url:{2}".format(query, e.message, self.m_url)))
            return self
        else:
            return self
    
    def utcnow(self):
        return datetime.datetime.now()
    
    def fromtimestamp(self):
        return datetime.datetime.fromtimestamp(float(self.data)) - datetime.timedelta(hours=8)
    

if __name__ == '__main__':
    # import requests
    
    # resp = requests.get("http://www.fashuounion.com/forum-270-1.html")
    # resp = requests.get("http://www.fashuounion.com/thread-421744-1-1.html")
    # resp.encoding = "gbk"
    # parser = Parser(data=resp.text)

    print "=".center(30, "=")
    #

    start = time.time()
    # print parser.xpath("//title").text().strip()
    # parser.remove_tree("//title")
    # print parser.xpath("//title").text().strip()
    # print Parser(data=parser.xpath("//title").text().strip()).regex("第二(\S+)校").text()
    # print Parser(data=parser.xpath("//title").text().strip()).regex(u"第二(\S+)校").text()
    # print parser.xpath('''(//div[@class="hm"]//span[@class="xi1"])[1]/text()''').int()
    # print parser
    # lll = parser.xpathall(".//table[@summary='forum_270']//tbody[contains(@id, 'thread')]")
    # for i in lll:
    #     i.xpath("(.//th[@class='new']|.//th[@class='common']|//th[@class='lock'])//a/text()").text().strip(), \
    #         i.xpath("(//th[@class='new']|//th[@class='common']|//th[@class='lock'])//a/@href").text().strip(), \
    #         i.xpath("(//td[@class='by'])[1]/em/span//text()").text().strip(), \
    #         i
        # print i.xpath("//text()").text(), i.xpath("//@href").text()
        # print i.xpath("//text()").data, i.xpath("//@href").data
    #     print i.regex(u"<p>(\S+)</p>").data
    # print parser.regex(u"<p>(\S+?)</p>").text()
    # parser1 = Parser(data='{"a":"b"}')
    # print parser1
    # print parser1.data
    # print parser1.html()
    # parser2 = Parser(
    #     data="<p>2019-06-26 17:11:54</p><span style='font-family:微软雅黑;'>text</span>tail",
    #     url="http://www.baidu.com/测试"
    # )
    # print parser2
    # print parser2.datetime()
    # print "1".center(30, "=")
    # print parser2.xpath("..//html//span[contains(@style, '微软')]").regex("微软(\S+)黑").text()
    #
    # parser3 = Parser(
    #     data="<li><a href='dddd.html'></a></li>",
    # )
    # l = parser3.xpathall("//li//a")
    # for i in l:
    #     print i.xpath("//@href").text()
    #
    # print parser2.xpath("//span[contains(@style, '微软')]").regex(u"微软(\S+)黑").text()
    # print parser2.xpath(u"//span[contains(@style, '微软')]").regex("微软(\S+)黑").text()
    # print parser2.xpath(u"//span[contains(@style, '微软')]").regex(u"微软(\S+)黑").text()
    #
    # print "2".center(30, "=")
    # print parser2.regex("微软(\S+)黑").text()
    # print parser2.xpath("//span[contains(@style, '爆炸')]").regex(u"微软(\S+)黑").text()
    # print parser2.xpath(u"//span[contains(@style, '爆炸')]").regex("微软(\S+)黑").text()
    # print parser2.xpath(u"//span[contains(@style, '爆炸')]").regex(u"微软(\S+)黑").text()
    #
    # print "3".center(30, "=")
    # print parser2.xpath("//span[contains(@style, '微软')]").text()
    # p = parser2.xpath(u"//span[contains(@style, '微软')]")
    # print p
    #
    # print "4".center(30, "=")
    # print parser2.xpath("").text()
    #
    # print "5".center(30, "=")
    # print parser2.data
    # print parser2.remove_tree(".//span[contains(@style, '微软')]/text()", with_tail=True)
    # print parser2.remove_tree(".//span[contains(@style, '微软')]", with_tail=True)
    # print parser2.data
    # print parser2
    # print time.time() - start
    #
    # root = etree.HTML("<html/>", parser=HTMLParser())
    # print etree.tostring(root, method="html", encoding="utf-8")

    parser2 = Parser(
            data="发稿时间：2020-03-18 20:48:14 "
                 "作者：中青报·中青网记者胡春艳 通讯员王鑫"
                 ""
                 "来源："
                 "中国青年报客户端",






            url="http://www.baidu.com/测试"
        )
    print parser2.datetime()