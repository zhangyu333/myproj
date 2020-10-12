#!/usr/bin/env python
# coding: utf-8
import re
import urlparse as parse
import traceback

from bs4 import BeautifulSoup, NavigableString, Tag, UnicodeDammit

'''
Copyright (c) 2017  - Beijing Intelligent Star, Inc.  All rights reserved
文件名：channels.py
功能：抽取新闻页面的面包屑导航


修改历史：
20170105：靳林林创建
'''

user_agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
headers = {
    'User-Agent': user_agent,
}
# key_symbol = '->|>>|>|&gt|»|›|＞|-|→'
# key_symbol_pattern = re.compile(r'%s' % key_symbol)
key_symbol = u'->|>|&gt|»|›|＞|-|→|—|>'
key_symbol_pattern = re.compile(r'(%s)+' % key_symbol)

time_pattern1 = re.compile(
    r'([1-2]\d{3}\D|\d{2}\D)([0-1]?\d[-月/\.][0-3]?\d)(日|\s*?|\|)(\s*?[0-2]?\d(:|点|时)[0-5]?\d(分|\s*?)(:\d{2}|)|\s*?)',
    re.DOTALL)
channel_error_time = re.compile(r'\d+?-\d*?')

# 判断导航长度临界值  201612271003修改
channel_lenth_judge = 8

zhengwen_keys = u'正文'
zhengwen_pattern = re.compile(r'%s' % zhengwen_keys)

location_keys = u'位置'
location_pattern = re.compile(r'%s' % location_keys)

first_keys = u'首页'
first_pattern = re.compile(r'%s' % first_keys)


def channel_soup_get(response_get, encoding):
    # 处理Windows-1252编码
    # print(encoding)
    negative_pattern = re.compile(
        r'<head[\s\S]*?</head>|<script[\s\S]*?</script>|<style[\s\S]*?</style>|<!--[\s\S]*?-->|'
        r'<title[\s\S]*?</title>|<option[\s\S]*?</option>',
        re.IGNORECASE)
    res_without_negative_content = re.sub(negative_pattern, '', response_get.content)

    try:
        # response_get.content.decode(encoding)
        res_without_negative_content.decode(encoding)
    except Exception:
        conrents = traceback.format_exc()
        return None, conrents
    # response_get.encoding = encoding

    # 清除script,css，以及display为none等无意义数据
    # negative_pattern = re.compile(
    #     r'<head[\s\S]*?</head>|<script[\s\S]*?</script>|<style[\s\S]*?</style>|<!--[\s\S]*?-->|'
    #     r'<title[\s\S]*?</title>|<option[\s\S]*?</option>',
    #     re.IGNORECASE)
    # res_without_negative_content = re.sub(negative_pattern, '', response_get.text)
    # channel_bsoup = BeautifulSoup(res_without_negative_content, 'lxml')

    res_without_negative_text = res_without_negative_content.decode(encoding)
    channel_bsoup = BeautifulSoup(res_without_negative_text, 'lxml')

    display_none = channel_bsoup.find_all(attrs={'style': re.compile('.*?display:none.*?')})
    if len(display_none) > 0:
        for i in display_none:
            i.extract()
            # 去除display = none的部分
    return channel_bsoup


def find_channel(tag):
    # 寻找包含导航标签 特殊符号的标签>|》|&gt
    for child in list(tag.children):
        if isinstance(child, NavigableString):
            if re.search(key_symbol_pattern, child.strip()) and len(child.strip()) < 25 \
                    and re.search(channel_error_time, child.strip()) is None:
                return tag
        else:
            find_channel(child)


# 找到包含某些文本的标签，在后面函数复用
def find_text(tag, text):
    if len(list(tag.stripped_strings)) == 1 and len(list(tag.parent.stripped_strings)) > 1:
        if re.search(text, list(tag.stripped_strings)[0].strip()) and len(list(tag.stripped_strings)[0]) < 4:
            return tag


def find_content(tag):
    # 查找包含正文的标签
    tag1 = find_text(tag, zhengwen_pattern)
    if tag1:
        return tag1
    else:
        for child in list(tag.children):
            if isinstance(child, NavigableString) and re.search(zhengwen_pattern, child.strip()) and len(
                    child.strip()) < 4:
                # if isinstance(child, NavigableString) and re.search(re.compile(r'正文'), child):
                return tag
            elif isinstance(child, NavigableString) is None:
                find_channel(child)


def find_location(tag):
    # 查找包含位置的标签
    tag1 = find_text(tag, location_pattern)
    if tag1:
        return tag1
    else:
        for child in list(tag.children):
            if isinstance(child, NavigableString) and re.search(location_pattern, child.strip()) and len(child) < 8:
                return tag
            elif isinstance(child, NavigableString) is None:
                find_channel(child)


def find_first(tag):
    # 查找包含首页的标签
    return find_text(tag, first_pattern)


def channel_content_get(channel_soup, url_channel):
    # 通过特殊符号来查找面包屑导航

    key_error_keys1_origin = u'关于我们|联系我们|相关链接|注册|更多|<|我顶|\['
    key_error_keys1 = key_error_keys1_origin
    key_error_symbol_pattern = re.compile(r'%s' % key_error_keys1)
    key_error_keys2_origin = u'查看'
    key_error_keys2 = key_error_keys2_origin
    key_error_symbol_pattern2 = re.compile(r'%s' % key_error_keys2)
    # 通过特殊关键符号查找导航所在标签
    channel_source = channel_soup.find_all(find_channel)
    # print('channel_source' + '=' * 40)
    # print(channel_source)
    # print(str(channel_source).decode('unicode_escape').encode('utf-8'))

    channel_content = None
    channel_len_index = None
    if len(channel_source) > 0:

        channel_len = 0
        for i in range(0, len(channel_source)):
            # print('channel_source[i]1' + '=' * 50)
            # print(channel_source[i])
            i_text = channel_source[i].get_text()
            key_symbol_content = re.search(key_symbol_pattern, i_text.strip()).group(0)

            # if re.search(re.compile(r'[\u4e00-\u9fa5\w]\s*(>|》|&gt)'), channel_source[i].get_text()) is None:
            # 特殊符号前后没有内容的，需要去父模块寻找
            while_num = 0
            while re.search(re.compile(r'(^(%s)$)' % (key_symbol_content,)),
                            i_text.strip()) is not None and while_num < 3:
                # 判断父元素的长度，剔除过长元素
                while_num += 1
                if len(list(channel_source[i].parent.stripped_strings)) < 15:
                    channel_source[i] = channel_source[i].parent
                    i_text = channel_source[i].get_text()

            #  修改20170109, 针对类似http://www.vr.cn/article/3540.html
            key_end_pattern = re.compile(r'(.*?(%s)$)' % (key_symbol_content,), re.DOTALL)
            if re.search(key_end_pattern,  channel_source[i].get_text().strip()) \
                    and len(list(i for i in channel_source[i].stripped_strings)) < channel_lenth_judge:
                channel_source[i] = channel_source[i].parent



        # 排除可能重复的元素
        channel_source = list(set(channel_source))
        for i in range(0, len(channel_source)):
            # print('channel_source[i]' + '=' * 50)
            # print(channel_source[i])

            # print(channel_source[i].get_text())
            # 找出具体的特殊符号
            key_symbol_content = re.search(key_symbol_pattern, channel_source[i].text.strip()).group(0)
            i_strings = list(channel_source[i].stripped_strings)
            i_text = ''.join(channel_source[i].get_text().split())
            # i_text = ''.join(list(k.strip() for k in i_strings))

            # 判断节点是否含有错误的关键词
            if re.search(key_error_symbol_pattern, channel_source[i].get_text().strip()):
                channel_source[i] = ''
                continue

            if re.search(ur'我顶', channel_source[i].get_text().strip()):
                channel_source[i] = ''
                continue

            # 根据关键符号分割关键词段落，根据标签内文本长度判断是否是真正的导航，临界值暂定为9（中国人民日报海外版）
            i_text_split = re.split(key_symbol_content, i_text)
            # if i_text_split[0] == '':

            # i_text_split.remove(i_text_split[0])

            for j in i_text_split:
                # 排除所有为空的元素

                if re.search(re.compile(r'^\s*?$'), j):
                    i_text_split.remove(j)

            # 包含查看关键字，并且只包含这一个部分，排除
            if len(i_text_split) == 1:
                if re.search(key_error_symbol_pattern2, i_text.strip()):
                    channel_source[i] = ''
                    continue

            # 如果特殊符号两边都有内容，并且内容属于同一个子节点，排除
            if len(i_text_split) > 1:
                if channel_source[i].string or len(list(channel_source[i].stripped_strings)) == 1:
                    channel_source[i] = ''
                    continue

            # ==判定分割文本后的第一个导航关键词的长度
            if len(i_text_split) == 0:
                channel_source[i] == ''
                continue
            elif len(i_text_split) == 1:
                key1 = i_text_split[0]
            else:
                key1 = i_text_split[1]
                if key1 == '':
                    key1 = i_text_split[0]
                elif len(i_text_split) == 2 and i_text_split[0] != '':
                    key1 = i_text_split[0]

            # 判定分割后的第一个关键词是否包含 你的位置 等信息
            key1_pattern = re.compile(u'：|%s' % location_keys)
            if re.search(key1_pattern, key1.strip()) is not None:
                key1 = re.split(key1_pattern, key1)[1]

            if len(key1.strip()) > 9:
                channel_source[i] = ''
                continue

            # ===判定所含子节点的长度，临界值为channel_lenth_judge
            i_lists = list()
            # 特殊符号最开始出现的位置
            len_i_strings = len(i_strings)
            for j in range(0, len_i_strings):
                if re.search(key_symbol_content, i_strings[j].strip()):
                    key_symbol_low_index = j
                    key_symbol_low_index -= 1
                    if key_symbol_low_index < 0:
                        key_symbol_low_index = 0

                    break

            # 特殊符号最后出现的位置
            i_strings_reverse = i_strings[::-1]
            key_symbol_high_index = None
            for j in range(0, len_i_strings):
                if re.search(key_symbol_content, i_strings_reverse[j]):
                    # 靠后的索引应该要比原本的取值范围大1
                    key_symbol_high_index = len(i_strings) - j + 1

                    break

            # 查找在特殊符号前后的有内容的节点
            for j in i_strings[key_symbol_low_index: key_symbol_high_index]:

                # 排除只包含特殊符号的文本
                if re.search(re.compile(r'(^(\s*%s\s*)$)' % (key_symbol_content,)), j.strip()) is None:
                    i_lists.append(j)

            channel_origin_list = list()
            i_lists_bak = list(i_lists)
            for m in channel_source[i].descendants:
                if m.string and m.string.strip() != '':

                    for n in i_lists_bak:
                        # 特殊符号间的字段提取
                        n1 = re.sub(re.compile('\+'), '\+', n)

                        if re.search(r'^(\s*?' + n1 + r'\s*?)$', unicode(m.string.strip())):
                            # if re.search(r'^(\s*' + n1 + '\s*?)$', m.string) or re.search(r'^(\s*' + n1 + '\s*?)$', m.string.encode('utf-8')):
                            i_lists_bak.remove(n)
                            channel_origin_list.append(m)
                            break
            # print('channel_origin_list' + '=' * 50)
            # print(channel_origin_list)

            # 所含子节点数量，增加确认
            if len(i_lists) < channel_lenth_judge and len(channel_origin_list) > 0:
                if key_symbol_low_index >= 0:
                    channel_origin_soup = BeautifulSoup('', 'lxml')
                    channel_origin0 = channel_origin_list[0].wrap(channel_origin_soup.new_tag('div'))

                    for x in channel_origin_list[1:]:
                        channel_origin0.append(x)

                    channel_source[i] = channel_origin0

                    # 特殊符号 - 涉及的干扰文本较多，所以排除两边非a标签的节点（有较低概率的误判，但相关频道标签参考意义也比较小）
                    if key_symbol_content == '-' and channel_origin0.find('a') is None:
                        channel_source[i] = ''

            else:
                channel_source[i] = ''

            # 确定面包屑导航所在的索引位置
            if isinstance(channel_source[i], Tag):

                if re.search(zhengwen_pattern, channel_source[i].get_text().strip()):
                    channel_content = channel_source[i]
                    # print('channel_content' + '=' * 40)
                    # print(channel_content)

                    return channel_content
                elif len(i_lists) > channel_len:
                    channel_len = len(channel_source[i])
                    channel_len_index = i

        # 确定面包屑导航所在
        if len(channel_source) == 1 and channel_source[0] != '':
            channel_content = channel_source[0]
        elif channel_content is None and channel_len_index is not None:
            # 不止一个符合条件时，选择更长的
            channel_content = channel_source[channel_len_index]

    if channel_content is None:
        # 新浪某些网页十分特殊，在金融等领域所占比例较大，特殊处理
        if 'sina' in url_channel:
            channel_content = channel_soup.find(class_="bread")

    # print('channel_content' + '=' * 40)
    # print(channel_content)
    return channel_content


def content_channels_get(channel_soup):
    # 通过‘正文’关键词查找导航标签
    content_channel_find = channel_soup.find_all(find_content)

    channel_content = None
    if len(content_channel_find) > 0:
        for i in range(0, len(content_channel_find)):

            # 查看包含正文关键字的标签有几个文本节点
            len_i = len(list(content_channel_find[i].stripped_strings))
            if len_i == 1:
                # 如果含有‘正文’的节点不包含其他节点，查看相关节点的父节点
                if len(list(content_channel_find[i].parent.stripped_strings)) < channel_lenth_judge:
                    channel_content = content_channel_find[i].parent
                    return channel_content
            elif len_i < channel_lenth_judge:
                channel_content = content_channel_find[i]
                return channel_content
    return channel_content


def first_channels_get(channel_soup):
    # 通过 ‘首页’关键词查找导航字段，排除包含“顶部”错误关键词的标签
    first_channel_find = channel_soup.find_all(find_first)

    channel_content = None
    channel_content_index = None
    if len(first_channel_find) > 0:
        first_len = len(list(first_channel_find[0].parent.stripped_strings))

        first_error_keys = u'顶部'
        first_error_pattern = re.compile(r'%s' % first_error_keys)
        for i in range(0, len(first_channel_find)):
            if len(list(first_channel_find[i].parent.stripped_strings)) < channel_lenth_judge:
                if re.search(first_error_pattern, first_channel_find[i].parent.get_text().strip()) is None:
                    first_channel_find[i] = first_channel_find[i].parent
                    i_len = len(list(first_channel_find[i].stripped_strings))
                    # 为了防止抓取到头部导航字段，选择包含子节点最少的标签
                    if i_len <= first_len:
                        first_len = i_len
                        channel_content_index = i

        if channel_content_index is not None:
            channel_content = first_channel_find[channel_content_index]

    return channel_content


def location_channels_get(channel_soup):
    # 通过 ‘位置’关键词查找导航标签
    location_channel_find = channel_soup.find_all(find_location)

    channel_content = None
    if len(location_channel_find) > 0:
        location_error_keys = u'字号'
        location_error_pattern = re.compile(r'%s' % location_error_keys)
        for i in range(0, len(location_channel_find)):

            # 查看包含位置关键字的标签包含几个文本节点
            len_i = len(list(location_channel_find[i].stripped_strings))
            if len_i == 1:
                # 如果含有‘位置’的节点不包含其他内容，查看相关节点的父节点
                if len(list(location_channel_find[i].parent.stripped_strings)) < channel_lenth_judge:
                    if re.search(location_error_pattern, location_channel_find[i].parent.get_text().strip()) is None:
                        channel_content = location_channel_find[i].parent
                        return channel_content
            elif len_i < channel_lenth_judge:
                if re.search(location_error_pattern, location_channel_find[i].get_text().strip()) is None:
                    channel_content = location_channel_find[i]
                    return channel_content
    return channel_content


def find_date(tag):
    # 寻找发表日期，从而寻找来源
    tag_strings = list(tag.stripped_strings)
    if len(tag_strings) == 1 and len(list(tag.parent.stripped_strings)) > 1:
        if re.search(time_pattern1, tag_strings[0].strip()) and len(tag_strings[0]) < 25:
            return tag


def date_channels_get(channel_soup, url_channel):
    # 通过日期来查找面包屑导航
    date_channel_find = channel_soup.find(find_date)

    channel_content = None
    if date_channel_find is not None:
        for element in date_channel_find.previous_elements:

            if element.name == 'a' and element.get_text() != '' and element.has_attr('href'):

                element_string = ''.join(list(element.stripped_strings))

                if parse.urlparse(element['href']).netloc == parse.urlparse(url_channel).netloc and len(
                        element_string) < 15:
                    # 外包一个标签，防止在最后单独的a标签无法找到自身
                    channel_origin_soup = BeautifulSoup('', 'lxml')
                    channel_content = element.wrap(channel_origin_soup.new_tag('div'))
                break
    return channel_content


def channel_result_get(channel_soup, url_channel):
    # 通过不同途径，最终确定面包屑导航所在
    channel_content_result = None
    channel_content1 = channel_content_get(channel_soup, url_channel)

    if channel_content1:
        channel_content_result = channel_content1
    else:
        channel_content2 = content_channels_get(channel_soup)
        if channel_content2:
            channel_content_result = channel_content2
        else:
            channel_content3 = first_channels_get(channel_soup)
            if channel_content3:
                channel_content_result = channel_content3
            else:
                channel_content4 = location_channels_get(channel_soup)
                if channel_content4:
                    channel_content_result = channel_content4
                else:
                    channel_content5 = date_channels_get(channel_soup, url_channel)
                    if channel_content5:
                        channel_content_result = channel_content5
    return channel_content_result


def channel_list_get(channel_content, url_channel):
    # 获取最后的频道层级列表
    channel_list = list()
    channel_tags = list()

    if channel_content is not None:
        channel_tag_a = channel_content.find_all('a', href=re.compile(r'.*'))
        if len(channel_tag_a) > 0:
            # 包含a标签的导航栏
            for i in channel_tag_a:
                channel_tags.append(i)
                i.extract()
                # 不包含a标签的导航栏
        content_text = channel_content.get_text()
        if re.search(key_symbol_pattern, content_text.strip()):
            # 包含特殊符号的处理
            key_symbol_content = re.search(key_symbol_pattern, content_text.strip()).group(0)
            channel_tags_others = re.split(key_symbol_content, content_text)
        else:
            # 没有包含特殊符号的处理
            if len(channel_tag_a) > 0:
                # 包含a标签，说明后面的内容都可能是在标签内，而不是所有内容在一个标签内
                channel_tags_others = list(i for i in channel_content.stripped_strings)
            else:
                channel_tags_others = content_text.split()
        for i in channel_tags_others:
            if i.strip() != "":
                channel_tags.append(i)

        if len(channel_tags) > 0:
            for i in range(0, len(channel_tags)):

                # 去除面包屑导航中的正文相关标签(有些事文章标题，所以判断长度)
                # if re.search(zhengwen_pattern, str(channel_tags[i])):
                # if re.search(zhengwen_pattern, channel_tags[i].encode('utf-8')):
                zhengwen_tag_pattern = re.compile(r'%s' % u'正文|文章内容|位置|more')
                if isinstance(channel_tags[i], Tag):
                    channel_tag_text = channel_tags[i].get_text()
                else:
                    channel_tag_text = channel_tags[i]

                if re.search(zhengwen_tag_pattern, channel_tag_text.strip().lower()) or len(
                        channel_tag_text.strip()) > 11:
                    continue

                channel_dict = dict()
                channel_dict['level'] = i + 1

                if hasattr(channel_tags[i], 'get_text'):
                    channel_dict['name'] = channel_tags[i].get_text().strip().encode('utf-8')
                else:
                    channel_dict['name'] = channel_tags[i].strip().encode('utf-8')

                if isinstance(channel_tags[i], Tag) and channel_tags[i].has_attr('href'):
                    # 去除链接为javascript 的导航
                    if re.search(ur'javascript', channel_tags[i]['href'].strip()) is None:
                        channel_dict['href'] = parse.urljoin(url_channel, channel_tags[i]['href']).encode('utf-8')
                    else:
                        channel_dict['href'] = 'none'.encode('utf-8')
                else:
                    channel_dict['href'] = 'none'.encode('utf-8')

                channel_list.append(channel_dict)
            #  去除明显不是频道导航的标签
            if len(channel_list) == 1 and re.search(r'^(评论|我的评论|收藏)$', channel_list[0]['name']):
                channel_list = []

    return channel_list


def news_channels_get(response_get, encoding):
    # gb2312 --> gbk
    if encoding and  "gb2312" in encoding.lower():
        encoding = "gbk"
    # 判断是否成功的参数
    judge = 0
    url_channel = response_get.url.encode('utf-8')
    if re.search(re.compile(r'^[45]'), str(response_get.status_code).strip()):
        # 有些404返回状态码200，需要进一步判断

        contents_url_error = url_channel + ' ' + str(response_get.status_code) + '错误'
        return judge, contents_url_error

    try:
        channel_soups = channel_soup_get(response_get, encoding)
    except Exception as e:
        contents_url_error = url_channel + '\n' + traceback.format_exc()
        return judge, contents_url_error

    if isinstance(channel_soups, str) and re.search(re.compile(r'^[45]'), channel_soups.strip()):
        contents_url_error = url_channel + ' ' + channel_soups + '错误'
        return judge, contents_url_error
    elif isinstance(channel_soups, tuple) and channel_soups[0] is None:
        contents_url_error = url_channel + '\n' + channel_soups[1]
        return judge, contents_url_error

    try:
        channel_content_result_get = channel_result_get(channel_soups, response_get.url)
    except Exception as e:
        contents_url_error = url_channel + '\n' + str(e) + '\n' + traceback.format_exc()
        return judge, contents_url_error

    try:
        channel_lists = channel_list_get(channel_content_result_get, url_channel=response_get.url)
    except Exception as e:
        # print(type(traceback.format_exc()))
        contents_url_error = url_channel + '\n' + traceback.format_exc()
        return judge, contents_url_error

    if len(channel_lists) == 0:
        judge = 2
        contents = url_channel
        return judge, contents

    else:
        judge = 1
        contents = channel_lists
        # print(channel_lists)
        return judge, contents


def bread_channels_result(response_get, encoding):
    final_result = news_channels_get(response_get, encoding)
    final_result_dict = {'judge': final_result[0], 'content': final_result[1]}
    return final_result_dict


if __name__ == '__main__':
    import requests
    import json

    url = 'http://www.gold678.com/dy/A/338279'
    url = 'http://stock.stockstar.com/JC2016120600002836.shtml'
    url = 'http://www.huaue.com/news2014/201717111407.htm'
    url = 'http://mobile.it168.com/a2017/0107/3087/000003087299.shtml'
    url = 'http://xinwen.eastday.com/a/170109012513217.html'
    # url = 'http://news.163.com/17/0106/00/CA2BEBGI00018AOQ.html'
    url = 'http://news.hexun.com/2016-08-23/185664846.html'
    resp = requests.get(url)
    print 1
    encoding = 'gbk'
    #encoding = 'utf-8'
    res = bread_channels_result(resp, encoding)
    print news_channels_get(resp, encoding)
    result = str(json.dumps(res['content'], encoding='utf-8', ensure_ascii=False))
    print result.decode("utf8")
