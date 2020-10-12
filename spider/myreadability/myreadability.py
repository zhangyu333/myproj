#! /usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import datetime
import traceback

from lxml.etree import tostring, tounicode
from lxml.html import fragment_fromstring, document_fromstring


from htmlparser import build_doc, to_string
from cleaners import html_cleaner, clean_attributes

import find_date
import channels_bread

#2015-02-11 18:07:00 | 2015-02-11 18:07
#2015年02月12日 06:48:00 | 2015年02月12日 06:48
REGEX_DATETIME = {
    'a': re.compile(u"(\d{1,4}\W\d{1,2}\W\d{1,2}\W?[  ]+?\d{1,2}:\d{1,2})", re.I|re.M|re.S),
    'b': re.compile(u"(\d{1,4}.\d{1,2}.\d{1,2}.\s*\d{1,2}:\d{1,2}(:\d{1,2}){0,1})", re.I|re.M|re.S),
    'c': re.compile(u"(\d{1,4}年\d{1,2}月\d{1,2})", re.I|re.M|re.S),
}


#pangwei add bdshare|bshare|copyright to 'negativeRe'
REGEXES = {
    'unlikelyCandidatesRe': re.compile('combx|comment|community|disqus|extra|foot|header|menu|remark|rss|shoutbox|sidebar|sponsor|ad-break|agegate|pagination|pager|popup|tweet|twitter|copyright', re.I),
    'okMaybeItsACandidateRe': re.compile('and|article|body|column|main|shadow', re.I),
    'positiveRe': re.compile('article|body|content|entry|hentry|main|page|pagination|post|text|blog|story', re.I),
    'negativeRe': re.compile('combx|comment|com-|contact|foot|footer|footnote|masthead|media|meta|outbrain|promo|related|scroll|shoutbox|sidebar|sponsor|shopping|tags|tool|widget|bdshare|bshare|jiathis|copyright|author|banquan|mzsm', re.I),
    'divToPElementsRe': re.compile('<(a|blockquote|dl|div|img|ol|p|pre|table|ul)', re.I),
    #'replaceBrsRe': re.compile('(<br[^>]*>[ \n\r\t]*){2,}',re.I),
    #'replaceFontsRe': re.compile('<(\/?)font[^>]*>',re.I),
    #'trimRe': re.compile('^\s+|\s+$/'),
    #'normalizeRe': re.compile('\s{2,}/'),
    #'killBreaksRe': re.compile('(<br\s*\/?>(\s|&nbsp;?)*){1,}/'),
    #'videoRe': re.compile('http:\/\/(www\.)?(youtube|vimeo)\.com', re.I),
    #skipFootnoteLink:      /^\s*(\[?[a-z0-9]{1,2}\]?|^|edit|citation needed)\s*$/i,
}


class Unparseable(ValueError):
    pass

regexp_type = type(re.compile('hello, world'))

def compile_pattern(elements):
    if not elements:
        return None
    if isinstance(elements, regexp_type):
        return elements
    if isinstance(elements, basestring):
        elements = elements.split(',')
    return re.compile(u'|'.join([re.escape(x.lower()) for x in elements]), re.U)


def get_distance(str1='', str2=''):
    min_len = min(len(str1), len(str2))
    max_len = max(len(str1), len(str2))
    common_num = 0.0
    for i in xrange(min_len):
        if str1[i] == str2[i]:
            common_num += 1.0
    return common_num  / max_len
    
    
class Document(object):
    """Class to build a etree document out of html"""
    TEXT_LENGTH_THRESHOLD = 25
    RETRY_LENGTH = 25

    def __init__(self, html, encoding=None, positive_keywords=None, negative_keywords=None, **kwargs):
        """Generate the document

        :param html: string of the html content.(unicode)

        kwargs:
            - attributes:
            - debug: output debug messages
            - min_text_length:
            - retry_length:
            - url: will allow adjusting links to be absolute
            - positive_keywords: the list of positive search patterns in classes and ids, for example: ["news-item", "block"]
            - negative_keywords: the list of negative search patterns in classes and ids, for example: ["mysidebar", "related", "ads"]
            Also positive_keywords and negative_keywords could be a regexp.
        """
        super(Document, self).__init__()

        self._html = html
        self.encoding = encoding
        self.kwargs = kwargs
        self.positive_keywords = compile_pattern(positive_keywords)
        self.negative_keywords = compile_pattern(negative_keywords)
        self._root = None
        self.url = kwargs.get('url', '')
        self._source_author = self.source_author
        self.source = self._source_author[0].encode('utf-8')
        self.author = self._source_author[1].encode('utf-8')

    def _build_doc(self, force=False):
        if force or self._root is None:
            self._root = self._parse(self._html)
        return self._root

    def _parse(self, html):
        etree, self.encoding = build_doc(html)
        etree = html_cleaner.clean_html(etree)
        base_href = self.kwargs.get('url', None)
        if base_href:
            etree.make_links_absolute(base_href, resolve_base_href=True)
        else:
            etree.resolve_base_href()
        return etree
    
    def is_list(self, *args, **kwargs):
        '''
        判读当前页是否为列表页
        '''
        try:
            etree = self._build_doc(True)
            body = etree.find(".//body")
            text = to_string(body)
            all_links = etree.findall(".//a")
            links_text = []
            for item in all_links:
                links_text.append(to_string(item))
                #print to_string(item)
            text_without_blank = re.compile(r"\s+", re.I|re.M|re.S).sub('', text)
            rate = len(''.join(links_text)) * 1.0 / len(text_without_blank)
            #print rate
            return rate > 0.6
        except:
            return False
    
    def urls(self):
        '''
        '''
        etree = self._build_doc(True)
        items = etree.xpath("//a/@href | //iframe/@src")
        urls = []
        for item in items:
            url = item.encode('utf8')
            if url.find('http') > -1:
                urls.append(url)
        return set(urls)
    
    def get_ctime(self):
        '''
        获取发布时间, 获取失败返回当前时间
        '''
        content = to_string(self._root.findall("body")[0]).decode('utf8')
        #print content
        utc_time = find_date._ctime_datetime(content, self.url)
        if utc_time:
            return utc_time - datetime.timedelta(hours=8)
        
        for prority, reg in REGEX_DATETIME.iteritems():
            m = reg.search(content)
            if m:
                str_ctime = m.group(1)
                fmt_ctime = re.sub("\W", " ", str_ctime)
                try:
                    utc_time = datetime.datetime.strptime(fmt_ctime, "%Y %m %d %H %M") - datetime.timedelta(hours=8)
                except:
                    try:
                        utc_time = datetime.datetime.strptime(fmt_ctime, "%Y %m %d") - datetime.timedelta(hours=8)
                    except:
                        utc_time = datetime.datetime.utcnow()
                return utc_time
        #print "----search ctime failed ---"
        return datetime.datetime.utcnow()

    def get_channel(self):
        u'''抽取频道'''
        etree, encoding = build_doc(self._html)
        response = self.kwargs.get('response', None)
        if not response:
            return ""
        try:
            result = channels_bread.news_channels_get(response, encoding)
        except Exception as e:
            traceback.print_exc()
            return ""
        if result[0] == 1:
            if result[1]:
                return result[1][-1].get('name', "")
        return ""
        

    @property
    def source_author(self):

        self._build_doc()
        source = ''
        author = ''

        prefix = u'来源|来自'



        import lxml.html
        def to_string2(elem):
            return lxml.html.tostring(elem, encoding='utf8', method='HTML', pretty_print=True).strip()

        try:
            content = to_string2(self._root.findall("body")[0]).decode('utf8')
        except:
            return '', ''

        content = re.sub('\s+', ' ', content)
        # print content
        text_list = re.findall('>([^<]+)<', content, re.U)

        def f(s):
            negative_regex = u'\d+$|阅读$|分享|点击|发现$|扫一扫$|即可将网页分享至朋友圈|字号$|评论|·|摘要|正文$|关闭$|网友评论$|^条$'
            if re.match(negative_regex, s) :
                return False
            else:
                return True
        from HTMLParser import HTMLParser
        h = HTMLParser()

        # 过滤函数
        s = lambda x: h.unescape(x).strip()

        # text_list = filter(bool, text_list)
        text_list = filter(f, text_list)
        text_list = filter(s, text_list)
        text_list = [s(i) for i in text_list]

        # 几个关键位置
        title_loc_list = []
        content_loc_list = []
        date_loc_list = []
        source_loc_list = []

        title_loc = 0
        content_loc = 0
        date_loc = 0
        source_loc = 0

        title = self.title.decode('utf-8').strip()
        title = re.sub('\s+', ' ', title)
        summary = self.summary(False).strip('\xc2\xa0').decode('utf-8').strip()

        # 获取标题文本

        h1_text = ''


        REGEX_DATETIME_dict = {
    'a': re.compile(u"(\d{1,4}\W\d{1,2}\W\d{1,2}\W?[  ]+?\d{1,2}:\d{1,2})", re.I|re.M|re.S),
    'b': re.compile(u"(\d{1,4}.\d{1,2}.\d{1,2}.\s*\d{1,2}:\d{1,2}(:\d{1,2}){0,1})", re.I|re.M|re.S),
    'c': re.compile(u"(\d{1,4}年\d{1,2}月\d{1,2})", re.I|re.M|re.S),
    'd': re.compile(u"(\d{1,2}月\d{1,2})", re.I|re.M|re.S),
    'e': re.compile(u"(\d{1,4}\.\d{1,2}\.\d{1,2})", re.I|re.M|re.S),
    'f': re.compile(u"(\d{1,4}-\d{1,2}-\d{1,2})", re.I|re.M|re.S)
}

        h1_text = title

        # print h1_text

        for i, text in enumerate(text_list):
            if text == h1_text:
                title_loc_list.append(i)
            if text in summary[:len(text)] and len(text)>5:
                # print text
                content_loc_list.append(i)
            for p, reg in REGEX_DATETIME_dict.items():
                if re.search(reg, text):
                    date_loc_list.append(i)
            if re.search(prefix, text, re.U):
                source_loc_list.append(i)

        if title_loc_list:
            title_loc = min(title_loc_list)

        if title_loc in content_loc_list:
            content_loc_list.remove(title_loc)

        if content_loc_list:
            content_loc = min(content_loc_list)

        if date_loc_list:
            date_loc = min(date_loc_list)

        if source_loc_list:
            source_loc = min(source_loc_list)

        # 获取 title位置，时间位置和正文位置
        # for loc in [title_loc, content_loc, date_loc, source_loc]:
        #     if loc:
        #         print loc, text_list[loc]
        #     else:
        #         print loc

        # print content_loc

        if title_loc and content_loc and content_loc != -1:
            # self.source_candidate = ' '.join(text_list[title_loc: content_loc])
            self.source_candidate = ' '.join(text_list[title_loc: max(content_loc, source_loc+2)])
            # print self.source_candidate
        elif source_loc and date_loc and abs(source_loc-date_loc) <=3:
            self.source_candidate = ' '.join(text_list[min(source_loc, date_loc): max(source_loc, date_loc)+2])
            # print self.source_candidate
        elif title_loc and date_loc and date_loc>title_loc:
            self.source_candidate = ' '.join(text_list[title_loc: date_loc+3])
            # print self.source_candidate
        elif date_loc:
            self.source_candidate = ' '.join(text_list[date_loc-2: date_loc+3])
            # print self.source_candidate

        else:
            if h1_text:
                title_loc = content.find(h1_text)

            if not title_loc:
                title_loc = content.find(title.decode('utf-8')[:10])
            # 正文位置
            # print self.summary(False).strip('\xc2\xa0').decode('utf-8')[:5]
            content_loc = content.find(self.summary(False).strip('\xc2\xa0').decode('utf-8')[:5])
            # print title_loc
            # print content_loc

            # 如果获取的文本长度太短，则加长他

            if title_loc == -1 and content_loc == -1:
                return '', ''

            if title_loc == -1:
                title_loc = content_loc/2

            if content_loc < title_loc+1000:
                content_loc = title_loc+1000

            # print title_loc
            # print content_loc

            self.source_candidate = content[title_loc: content_loc]
            # print self.source_candidate

        def get_source_candidate():
            # print self.source_candidate
            self.source_candidate = re.sub('\s+', ' ', self.source_candidate, re.U)
            self.source_candidate = self.source_candidate.replace(title, '')
            # print self.source_candidate

            candidate_list = re.findall('>([^<]+)<', self.source_candidate, re.U)
            if not candidate_list:
                candidate_list = self.source_candidate.split()
            from HTMLParser import HTMLParser
            h = HTMLParser()

            # 过滤函数
            s = lambda x: h.unescape(x).strip()
            candidate_list = filter(s, candidate_list)

            self.source_candidate = ' '.join(candidate_list)
            self.source_candidate = h.unescape(self.source_candidate)
            noisy = ur':|：|\（|\(|\)|\）'
            self.source_candidate = self.source_candidate.replace('http:', 'http@')
            self.source_candidate = re.sub(noisy, ' ', self.source_candidate)
            # print self.source_candidate

        get_source_candidate()


        if self.source_candidate:
            source, author = self.get_weight()
        if source or author:
            return source, author
        else:
            source_loc = content.find(u'来源')
            if source_loc != -1:
                self.source_candidate = content[source_loc-200: source_loc+200]
                get_source_candidate()
                source, author = self.get_weight()
                if re.match(u'(.*?网|报)', summary, re.U):
                    source_p = re.match(u'(.*?网|报)', summary, re.U).group(1)
                    if len(source_p)<10:
                        source = source_p
                return source, author

        return source, author

    def get_weight(self):

        # print self.source_candidate

        source = ''
        author = ''

        candidate_list = self.source_candidate.split()
        # print self.source_candidate

        if not candidate_list:
            return '', ''

        def f(s):
            negative_regex = u'^\d+$|阅读$|分享|点击|发现$|扫一扫$|即可将网页分享至朋友圈|字号$|评论|·|^中$|^小$|^大$|\||^次$|^收藏$'
            if re.match(negative_regex, s) :
                return False
            else:
                # if len(s)> 15:
                #     return False
                # else:
                    return True

        # 过滤，去掉无用的内容
        # print ' '.join([i.encode('utf-8') for i in candidate_list])
        candidate_list = filter(f, candidate_list)
        # print candidate_list
        # print ' '.join([i.encode('utf-8') for i in candidate_list])

        # 几个有用的参数：日期的位置，作者的位置，来源的位置
        source_index = None
        author_index = None
        date_index = None
        edior_index = None

        postfix = ur'(报|网)$'
        prefix = u'来源|来自|发布者'
        author_regex = u'作者'
        editor_regex = u'编辑'

        weight_list = [1 for _ in candidate_list]

        REGEX_DATETIME_dict = {
    'a': re.compile(u"(\d{1,4}\W\d{1,2}\W\d{1,2}\W?[  ]+?\d{1,2}:\d{1,2})", re.I|re.M|re.S),
    'b': re.compile(u"(\d{1,4}.\d{1,2}.\d{1,2}.\s*\d{1,2}:\d{1,2}(:\d{1,2}){0,1})", re.I|re.M|re.S),
    'c': re.compile(u"(\d{1,4}年\d{1,2}月\d{1,2})", re.I|re.M|re.S),
    'd': re.compile(u"(\d{1,2}月\d{1,2})", re.I|re.M|re.S),
    'e': re.compile(u"(\d{1,4}.\d{1,2}.\d{1,2})", re.I|re.M|re.S)
}

        if len(candidate_list) > 1:
            for c, w, i in zip(candidate_list, weight_list, range(len(weight_list))):

                for prority, reg in REGEX_DATETIME_dict.iteritems():
                    m = re.search(reg, c)
                    if m:
                        # print prority
                        date_index = i
                        if i > 0:
                            weight_list[i-1] *= 5
                        if i < len(weight_list) -1:
                            weight_list[i+1] *= 5
                        break

                if re.search(prefix, c, re.U) and len(c) < 4 :
                    source_index = i
                    candidate_list[i] = 'source'
                    weight_list[i] /= 10.0 if re.search(prefix, candidate_list[i], re.U) else 1
                    if i<len(weight_list)-1:
                        weight_list[i+1] *= 10 if re.search(prefix, candidate_list[i], re.U) else 1

                weight_list[i] *= 10 if c.startswith('http') or c.startswith('www.') else 1

                if re.search(author_regex, c, re.U):
                    author_index = i
                    candidate_list[i] = 'author'

                if re.search(editor_regex, c, re.U):
                    edior_index = i
                    candidate_list[i] = 'editor'

                weight_list[i] *= 20 if re.search(postfix, c, re.U) and len(c)<10 else 1



        # print candidate_list
        # print weight_list
        # for c, w in zip(candidate_list, weight_list):
        #     print c, w

        if author_index is not None and author_index <= len(candidate_list)-2:
            author = candidate_list[author_index+1]
            if author in ['editor', 'source']:
                author = ''
            # print '作者：', author
        if source_index is not None :
            if source_index < len(weight_list)-1:
                source = candidate_list[source_index+1]
                if source in ['author', 'editor', 'source'] :
                    source = ''
            # print '来源：', source
        else:
            if max(weight_list) > 1:
                max_index = weight_list.index(max(weight_list))
                # print max_index
                source = candidate_list[max_index]
                # print '来源：', source
            else:
                pass
                # print '没有找到来源'

        # 如果候选列表只有3个元素，一个为日期，一个为网站，则剩下的为编辑，不太可靠。没想到更好的办法。。。。
        # print source
        if len(candidate_list) == 3 and date_index is not None and source:
            # candidate_list.remove(candidate_list[date_index])
            # candidate_list.remove(source)
            author = candidate_list[0]
            if len(author) > 20 or author in ['source']:
                author = ''

        if len(source)>20:
            source = ''
        return source, author

    @property
    def title(self):
        return self.get_title()
    
    def get_title(self):
        title = ''
        etree = self._build_doc(True)
        if etree is not None:
            node_title = etree.find(".//title")
            if node_title is not None:
                title =  to_string(node_title)
                title_array = re.split("—|_|-|-\||\|", title)
                title = title_array[0]
                if len(title_array) >= 2:
                    if re.search("网$|日报$", title) is not None and len(title) < len(title_array[1]):
                        title = title_array[1]
            
            node_title = etree.find(".//h1")
            if node_title is not None:
                head_title = to_string(node_title)
                distance = get_distance(title, head_title)
                if distance > 0.6:
                    title = head_title
            
        return title
    
    def get_clean_html(self):
        return clean_attributes(to_string(self._root))
        return clean_attributes(tostring(self._root, encoding='utf-8'))
        return clean_attributes(tounicode(self._root))
    
    def tags(self, node, *tag_names):
        for tag in tag_names:
            for elem in node.findall(".//%s"%tag):
                yield elem
    
    def reverse_tags(self, node, *tag_names):
        for tag_name in tag_names:
            for e in reversed(node.findall('.//%s' % tag_name)):
                yield e
    
    
    def summary(self, html_partial=False):
        """Generate the summary of the html docuemnt
        :param html_partial: return only the div of the document, don't wrap
        in html and body tags.
        """
        try:
            ruthless = True
            while 1:
                self._build_doc(True)
                #pangwei add on 2014/12/08 begin
                for elem in self.tags(self._root, 'footer', 'select'):
                    elem.drop_tree()
                #pangwei add on 2014/12/08 end
                for elem in self.tags(self._root, 'script', 'style'):
                    elem.drop_tree()
                for elem in self.tags(self._root, 'body'):
                    elem.set('id', 'readabilityBody')
                if ruthless:
                    self.remove_unlikely_candidates()
                self.transform_misused_divs_into_paragraphs()
                
                candidates = self.score_paragraphs()
                best_candidate = self.select_best_candidate(candidates)
                if best_candidate:
                    article = self.get_article(candidates, best_candidate,html_partial=html_partial)
                else:
                    if ruthless:
                        ruthless = False
                        continue
                    else:
                        article = self._root.find('body')
                        if article is None:
                            article = self._root
                
                cleaned_article = self.sanitize(article, candidates)
                article_length = len(cleaned_article or '')
                retry_length = self.kwargs.get('retry_length',self.RETRY_LENGTH)
                of_acceptable_length = article_length >= retry_length
                if ruthless and not of_acceptable_length:
                    ruthless = False
                    continue
                else:
                    return cleaned_article
            
        except StandardError, e:
            raise Unparseable(str(e)), None, sys.exc_info()[2]
    
    def get_article(self, candidates, best_candidate, html_partial=False):
        # Now that we have the top candidate, look through its siblings for
        # content that might also be related.
        # Things like preambles, content split by ads that we removed, etc.
        sibling_score_threshold = max([10, best_candidate['content_score'] * 0.2])
        
        if html_partial:
            output = fragment_fromstring('<div/>')
        else:
            output = document_fromstring('<div/>')
        best_elem = best_candidate['elem']
        for sibling in best_elem.getparent().getchildren():
            append = False
            if sibling is best_elem:
                append = True
            sibling_key = sibling
            if sibling_key in candidates and \
                candidates[sibling_key]['content_score'] >= sibling_score_threshold:
                append = True
            
            if sibling.tag == "p":
                link_density = self.get_link_density(sibling)
                node_content = sibling.text or ""
                node_length = len(node_content)
                
                if node_length > 80 and link_density < 0.25:
                    append = True
                elif node_length <= 80 \
                    and link_density == 0 \
                    and re.search('\.( |$)', node_content):
                    append = True
            
            if append:
                # We don't want to append directly to output, but the div
                # in html->body->div
                if html_partial:
                    output.append(sibling)
                else:
                    output.getchildren()[0].getchildren()[0].append(sibling)
        #if output is not None:
        #    output.append(best_elem)
        return output
    
    
    def remove_unlikely_candidates(self):
        for elem in self._root.iter():
            #pangwei add on 2014/12/15 start
            style = "%s"%elem.get('style', '').lower()
            if re.search("display:none", style):
                #print  "--Drop display:none tree: tag:%s; id:%s; class:%s"%(elem.tag, elem.get('id'), elem.get('class'))
                elem.drop_tree()
                continue
            #pangwei add on 2014/12/15 stop
            
            s = "%s %s" % (elem.get('class', ''), elem.get('id', ''))
            if len(s) < 2:
                continue
            
            if REGEXES['unlikelyCandidatesRe'].search(s) and \
                (not REGEXES['okMaybeItsACandidateRe'].search(s)) and \
                elem.tag not in ['html', 'body']:
                elem.drop_tree()
                #print "--drop: ", elem.tag, '---:----',  describe(elem), elem.text_content()
    
    def transform_misused_divs_into_paragraphs(self):
        '''
    # transform <div>s that do not contain other block elements into <p>s
    # FIXME: The current implementation ignores all descendants that
    # are not direct children of elem
    # This results in incorrect results in case there is an <img>
    # buried within an <a> for example
    '''
        for elem in self.tags(self._root, 'div'):
            style = "%s"%elem.get('style', '').lower()
            if re.search("display:none", style):
                #print  "--Drop display:none tree--: tag:%s; id:%s; class:%s"%(elem.tag, elem.get('id'), elem.get('class'))
                elem.drop_tree()
                continue
            if not REGEXES['divToPElementsRe'].search(unicode(''.join(map(tostring, list(elem))))):
                #pangwei modify on 2014/12/17 begin
                #elem.tag = "p"
                #pangwei modify end
                #pangwei add on 2014/12/17 begin
                p = fragment_fromstring('<p/>')
                p.text = elem.text
                elem.text = None
                elem.text = None
                elem.insert(0, p)
                #pangwei add end
        
        for elem in self.tags(self._root, 'div'):
            if elem.text and elem.text.strip():
                p = fragment_fromstring('<p/>')
                p.text = elem.text
                elem.text = None
                elem.insert(0, p)
                #print "Inserted "+ tounicode(p)+" to " + describe(elem)
            
            for pos, child in reversed(list(enumerate(elem))):
                if child.tail and child.tail.strip():
                    p = fragment_fromstring('<p/>')
                    p.text = child.tail
                    child.tail = None
                    elem.insert(pos + 1, p)
                    #print "Inserted "+ tounicode(p)+" to " + describe(elem)
                if child.tag == 'br':
                    #print 'Dropped <br> at '+ describe(elem)
                    child.drop_tree()
                if child.tag == 'strong':
                    child.tag = 'p'
    
    
    def score_paragraphs(self):
        '''
        计算节点分值
        '''
        ordered = []
        candidates = {}
        MIN_LEN = self.kwargs.get('min_text_length', self.TEXT_LENGTH_THRESHOLD)
        
        for elem in self.tags(self._build_doc(), "p", "pre", "td"):
            parent_node = elem.getparent()
            if parent_node is None:
                continue
            grand_parent_node = parent_node.getparent()
            
            inner_text = clean(elem.text_content() or "")
            inner_text_len = len(inner_text)
            
            if inner_text_len < MIN_LEN:
                continue
            
            if parent_node not in candidates:
                candidates[parent_node] = self.score_node(parent_node)
                ordered.append(parent_node)
                
            if grand_parent_node is not None and grand_parent_node not in candidates:
                candidates[grand_parent_node] = self.score_node(grand_parent_node)
                ordered.append(grand_parent_node)
            
            content_score = 1
            #pangwei comments on 2014/12/15 begins
            #content_score += len(inner_text.split(','))
            #content_score += min((inner_text_len / 100), 3)
            #pangwei comments on 2014/12/15 end
            ##pangwei add on 2014/12/15 begins
            content_score += len(re.split(",|，", inner_text))
            content_score += max((inner_text_len / 25), 0)
            ##pangwei add on 2014/12/15 end
            #if elem not in candidates:
            #    candidates[elem] = self.score_node(elem)
            #WTF? candidates[elem]['content_score'] += content_score
            candidates[parent_node]['content_score'] += content_score
            if grand_parent_node is not None:
                candidates[grand_parent_node]['content_score'] += content_score/2.0
            
        # Scale the final candidates score based on link density. 
        # Good content should have a relatively small link density (5% or less)
        #  and be mostly unaffected by this operation.
        for elem in ordered:
            candidate = candidates[elem]
            ld = self.get_link_density(elem)
            #score = candidate['content_score']
            candidate['content_score'] *= (1 - ld)
        
        return candidates
    
    
    def score_node(self, elem):
        content_score = self.class_weight(elem)
        name = elem.tag.lower()
        if name == "div":
            content_score += 5
        elif name in ["pre", "td", "blockquote"]:
            content_score += 3
        elif name in ["address", "ol", "ul", "dl", "dd", "dt", "li", "form"]:
            content_score -= 3
        elif name in ["h1", "h2", "h3", "h4", "h5", "h6", "th"]:
            content_score -= 5
        #pangwei add 2014/12/10 begin:
        elif name in ["select"]:
            content_score -= 5
        #pangwei add 2014/12/10 end
        return {
            'content_score': content_score,
            'elem': elem
        }
    
    
    def class_weight(self, e):
        weight = 0
        for feature in [e.get('class', None), e.get('id', None)]:
            if feature:
                if REGEXES['negativeRe'].search(feature):
                    weight -= 25
                if REGEXES['positiveRe'].search(feature):
                    weight += 25
                if self.positive_keywords and self.positive_keywords.search(feature):
                    weight += 25
                if self.negative_keywords and self.negative_keywords.search(feature):
                    weight -= 25
        if self.positive_keywords and self.positive_keywords.match('tag-'+e.tag):
            weight += 25
        if self.negative_keywords and self.negative_keywords.match('tag-'+e.tag):
            weight -= 25
        
        return weight
    
    def select_best_candidate(self, candidates):
        sorted_candidates = sorted(candidates.values(), key=lambda x: x['content_score'], reverse=True)
        for candidate in sorted_candidates[:5]:
            elem = candidate['elem']
            #print describe(elem)
        
        if len(sorted_candidates) == 0:
            return None
        
        best_candidate = sorted_candidates[0]
        
        return best_candidate
        
    def get_link_density(self, elem):
        link_length = 0
        for i in elem.findall(".//a"):
            link_length += text_length(i)
        total_length = text_length(elem)
        return float(link_length) / max(total_length, 1)
    
    def sanitize(self, node, candidates):
        '''对输出结果做最后的清洗
        '''
        MIN_LEN = self.kwargs.get('min_text_length',self.TEXT_LENGTH_THRESHOLD)
        
        #清除不满足条件的"h1", "h2", "h3", "h4", "h5", "h6", 根据class,id和link density
        for header in self.tags(node, "h1", "h2", "h3", "h4", "h5", "h6"):
#            if self.class_weight(header) < 0 or self.get_link_density(header) > 0.33:
            if self.class_weight(header) <= 0 or self.get_link_density(header) > 0.33:
                header.drop_tree()
        
        for elem in self.tags(node, "form", "iframe", "textarea"):
            elem.drop_tree()
        
        allowed = {}
        # Conditionally clean <table>s, <ul>s, and <div>s
        for el in self.reverse_tags(node, "table", "ul", "div"):
            if el in allowed:
                continue
            
            weight = self.class_weight(el)
            if el in candidates:
                content_score = candidates[el]['content_score']
            else:
                content_score = 0
            tag = el.tag
            if weight + content_score < 0:
                el.drop_tree()
            elif el.text_content().count(",") < 10:
                counts = {}
                for kind in ['p', 'img', 'li', 'a', 'embed', 'input']:
                    counts[kind] = len(el.findall('.//%s' % kind))
                counts["li"] -= 100
                counts["input"] -= len(el.findall('.//input[@type="hidden"]'))
                
                # Count the text length excluding any surrounding whitespace
                content_length = text_length(el)
                link_density = self.get_link_density(el)
                parent_node = el.getparent()
                if parent_node is not None:
                    if parent_node in candidates:
                        content_score = candidates[parent_node]['content_score']
                    else:
                        content_score = 0
#                 if parent_node is not None:
#                     pweight = self.class_weight(parent_node) + content_score
#                     pname = describe(parent_node)
#                 else:
#                     pweight = 0
#                     pname = "no parent"
                to_remove = False
                reason = ""
                if counts["p"] and counts["img"] > counts["p"]:
                    reason = "too many images (%s)" % counts["img"]
                    to_remove = True
                elif counts["li"] > counts["p"] and tag != "ul" and tag != "ol":
                    reason = "more <li>s than <p>s"
                    to_remove = True
                elif counts["input"] > (counts["p"] / 3):
                    reason = "less than 3x <p>s than <input>s"
                    to_remove = True
                elif content_length < (MIN_LEN) and (counts["img"] == 0 or counts["img"] > 2):
                    reason = "too short content length %s without a single image" % content_length
                    to_remove = True
                elif weight < 25 and link_density > 0.2:
                    reason = "too many links %.3f for its weight %s" % (link_density, weight)
                    to_remove = True
                elif weight >= 25 and link_density > 0.5:
                    reason = "too many links %.3f for its weight %s" % (link_density, weight)
                    to_remove = True
                elif (counts["embed"] == 1 and content_length < 75) or counts["embed"] > 1:
                    reason = "<embed>s with too short content length, or too many <embed>s"
                    to_remove = True
                    #find x non empty preceding and succeeding siblings
                    i, j = 0, 0
                    x = 1
                    siblings = []
                    for sib in el.itersiblings():
                        sib_content_length = text_length(sib)
                        if sib_content_length:
                            i =+ 1
                            siblings.append(sib_content_length)
                            if i == x:
                                break
                    for sib in el.itersiblings(preceding=True):
                        sib_content_length = text_length(sib)
                        if sib_content_length:
                            j =+ 1
                            siblings.append(sib_content_length)
                            if j == x:
                                break
                    if siblings and sum(siblings) > 1000:
                        to_remove = False
                        for desnode in self.tags(el, "table", "ul", "div"):
                            allowed[desnode] = True
                    
                if to_remove:
                    #print "--Cleaned %6.3f %s with weight %s cause it has %s : %s"%(content_score, describe(el), weight, reason, el.text_content())
                    el.drop_tree()
                
        for el in ([node] + [n for n in node.iter()]):
            if not self.kwargs.get('attributes', None):
                pass
        
        #pangwei add begin on 2014/12/15
        #版权申明开始标志
        flag = False
        for elem in self.tags(node, 'p'):
            if flag:
                if elem.getparent() is not None:
                    elem.drop_tree()
                    continue
                    #print "-*--*--*- Dropped: content: %s ; type:%s"%(content, type(content))
            content = elem.text_content().strip()
            if re.search(u"版权说明|版权声明|免责声明", content[:12]):
                if elem.getparent() is not None:
                    elem.drop_tree()
                    #print "-*- content: %s ; type:%s"%(content, type(content))
                flag = True
                continue
            if re.search(u"说明|声明|注明", content[:12]):
                if re.search(u"转载|版权", content) and re.search(u"传播|授权|不代表", content):
                    if elem.getparent() is not None:
                        elem.drop_tree()
                        #print "-*--*- content: %s ; type:%s"%(content, type(content))
                    flag = True
                    continue
        #pangwei add end on 2014/12/15 
        
        self._root = node
        
        return self.get_clean_html()

    
    def open_in_browser(self):
        import lxml.html
        return lxml.html.tostring(self._root)
    
    #pangwei add on 2014/12/22 begin
    def get_detail_list_content(self):
        pass
    #pangwei add on 2014/12/22 end
    
    
def describe(node, depth=1):
    if not hasattr(node, 'tag'):
        return "[%s]" % type(node)
    name = node.tag
    if node.get('id', ''):
        name += '#' + node.get('id')
    if node.get('class', ''):
        name += '.' + node.get('class').replace(' ', '.')
    if name[:4] in ['div#', 'div.']:
        name = name[3:]
    if depth and node.getparent() is not None:
        return name + ' - ' + describe(node.getparent(), depth - 1)
    return name
    
def clean(text):
    text = re.sub('\s*\n\s*', '\n', text)
    text = re.sub('[ \t]{2,}', ' ', text)
    return text.strip()

def text_length(elem):
    return len(clean(elem.text_content() or ""))


if __name__ == "__main__":
    import requests
    
#    d = get_distance('hello', 'helo')
#    print "--distacne: ", d
    
    
    url = 'http://epaper.subaonet.com/szrb/html/2014-12/17/content_303187.htm'
    url = 'http://xjrb.xjdaily.com/jryw/1161369.shtml'
    #url = 'http://news.koolearn.com/20141215/1035865.html'
    url = 'http://news.sdchina.com/show/3158209.html'
    #copyright
    url = 'http://finance.sina.com.cn/china/hgjj/20141217/192721100957.shtml'
    url = 'http://xjrb.xjdaily.com/jryw/1161369.shtml'
    url = 'http://www.10yan.com/2014/1218/149013.shtml'
#    url = 'http://news.china.com.cn/node_7115409.htm'
#    url = 'http://www.aikao.com/html/1245/41936.html'
    url = 'http://finance.qq.com/a/20141226/000899.htm?pgv_ref=aio2012&ptlang=2052'
#    url = 'http://news.xinhuanet.com/politics/2014-12/23/c_1113752344.htm'
#    url = 'http://ts.hebnews.cn/2015-01/04/content_4440338.htm#'
#    url = 'http://house.enorth.com.cn/system/2015/01/08/012390387.shtml'
#    url = 'http://news.dahe.cn/2015/01-22/104168123.html#'
#    url = 'http://news.xinhuanet.com/politics/2015-02/05/c_127459235.htm'
    url = 'http://www.thepaper.cn/newsDetail_forward_1301303'
    url = 'http://hebei.hebnews.cn/2014-09/12/content_4169408.htm'
    url = 'http://news.cnnb.com.cn/system/2006/03/20/005090532.shtml'
    url = 'http://news.16888.com/a/2014/0903/539638.html'
    url = 'http://news.ifeng.com/a/20150429/43658999_0.shtml'
    url = 'http://tieba.baidu.com/p/2958122545'
    url = 'http://www.eastobacco.com/ycr/201501/t20150112_354115.html'
    url = 'http://www.chinacourt.org/article/detail/2011/02/id/441623.shtml'
    url ='http://hy.southcn.com/content/2015-07/22/content_128939599.htm#'
#    url = 'http://t.cn/RLi7bux'
    url = 'http://astro.sina.com.cn/t/2015-08-14/doc-ifxfxzzn7469512.shtml'
    # url = 'http://www.slrbs.com/shyf/shenghuoyufa/2014-10-08/203212.html#'
    # url = 'http://www.weibo.com/p/230418638695670102wy6u'
    # url = 'http://www.chinadaily.com.cn/dfpd/dfkeji/2015-01-08/content_13001765.html#'
    # url = 'http://www.xinjiangyaou.com/xinjiang/008/1382617.shtml'
    url = 'http://news.cnhubei.com/ctjb/ctjbsgk/ctjb15/200911/t857020.shtml'
    url = 'http://news.cqnews.net/html/2016-08/24/content_38207389.htm'
    url = 'http://epaper.ynet.com/html/2016-08/24/content_214775.htm'
    url = 'http://www.weishan.cc/article-53377-1.html'
    url = 'http://www.chinapipe.net/project/d791381.html'
    url = 'http://stock.10jqka.com.cn/20121031/c530533259.shtml'
    #url = 'http://news.hexun.com/2016-08-23/185664846.html'
    url = 'http://tech.sina.com.cn/t/2016-08-30/doc-ifxvixer7496198.shtml'
    
    resp = requests.get(url)
    html = resp.content
    
#     f = open('d:\\temp\\extractor\\1.html', 'rb')
#     html = f.read()
#     #f.write(html)
#     f.close()
#    print "--html: ", html
    
    negative = ['bodytitle', 'pub_date', 'banquan']
#      
    doc = Document(html, url=url, response=resp)
     
    title =  doc.title
    print url
    print "--title: ", title
    print "--encoding: ", doc.encoding
    print doc.get_ctime()
    print doc.get_channel().decode('utf8')
    # print doc.summary(False)
    print doc.source.decode('utf8')
    
#    print doc.is_list()
