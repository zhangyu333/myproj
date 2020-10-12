# -*- coding:utf-8 -*- 
import re
import datetime
import traceback
import HTMLParser
from lxml.html.clean import Cleaner


def filter_invalid_tags(text):
    '''去除注释 style script'''
    html_cleaner = Cleaner(scripts=True, javascript=True, comments=True, style=True,
        links=False, meta=False, page_structure=False, processing_instructions=False,
        embedded=False, frames=False, forms=False, annoying_tags=False, remove_tags=None,
        remove_unknown_tags=False, safe_attrs_only=False)
    text = html_cleaner.clean_html(text)
    return text

#当前年份的前两位
cur_year_2 = str(datetime.date.today().year / 100)

class GetDate(object):
    class DateStruct(object):
        def __init__(self):
            self.datetime=None
            self.weight = 10
            self.position = 0
            htmlFragment = ""
    class WeightStruct(object):
        def __init__(self, tag, weight):
            self.tag = tag
            self.weight = weight


    def getDate(self, html, url=''):

        isUnicode = True
        codePos = html.find("charset=")
        code = html[codePos+9:codePos+11].lower()
        if not isinstance(html, unicode):
            if code=='gb' or code=='b2' or code=='b1' or code=='bk':
                try:
                    html=unicode(html,'gbk','ignore')
                except:
                    #print "error1"
                    isUnicode = False
    
            elif code=='ut' or code=='tf':
                try:
                    html=unicode(html,'utf-8','ignore')
                except:
                    #print "error2"
                    isUnicode = False
            else:
                try:
                    html=unicode(html,'BIG5')
                except:
                    try:
                        html=unicode(html,'utf-8')
                    except:
                        try:
                            html=unicode(html,'gbk','ignore')
                        except:
                            #print "error3"
                            isUnicode = False
        if isUnicode:       
            html=self.__denoise(html)
        dateList = self.__getAllDateFromText(html,10,isUnicode)
        urlDateList = self.__getAllDateFromText(url,15,isUnicode)
        dateList = self.__addWeight(dateList,isUnicode)

        for dateItem in urlDateList:
            dateList.append(dateItem)

        dateList.sort(key=lambda date:date.weight, reverse=True )
        
        self.__printResult(dateList)
    
        if len(dateList)>0:
            dt=dateList[0]
            return dt.datetime
        else:
            return None
    
    def __getAllDateFromText(self, text, weight,isUnicode):
        u'''
        负责提取一段文本中的时间，调formatDate格式化时间，提取时间附近的上下文（前后50个字符）
        input： text------一段文本
                weight----默认权值
        output：dateList------返回的DateStruct型的列表        
        '''
        dateList=[]
        regexp=u"(?:(?:19)?9\d|(?:20)?[01][0-9])(?:[-\s\/.,、年]|&#24180;)(?:[01]?[0-9])(?:[-\s\/.,、月]|&#26376;)(?:[0-3]?[0-9])(?:日|&#26085;)?(?:\s|\\xa0){0,3}(?:[0-2]?\d:[0-5]?\d(?::[0-5]?\d)?)?"
        if not isUnicode:
            regexp=u"(?:(?:19)?9\d|(?:20)?[01][0-9])[-\s\/.,](?:[01]?[0-9])[-\s\/.,](?:[0-3]?[0-9])(?:\s|\\xa0){0,3}(?:[0-2]?\d:[0-5]?\d(?::[0-5]?\d)?)?"
        date_str_list=re.findall(regexp,text,re.I|re.M|re.S)
        for date in date_str_list:
            pos=text.find(date)
            formatedDate=self.__formatDate(date)
            if pos>0 and formatedDate:
                length=len(date)
                currDate=self.DateStruct()
                try:
                    currDate.datetime = datetime.datetime(int(formatedDate['year']),int(formatedDate['month']),int(formatedDate['day']),int(formatedDate['time'][:2]),int(formatedDate['time'][3:5]),int(formatedDate['time'][6:8])) 
                except:
                    continue
                currDate.position=pos
                currDate.weight=weight
                if len(date)>7:
                    if (date[4]=='-' and date[7]=='-') or (date[4]=='-' and date[6]=='-'):
                        currDate.weight*=1.5
                if u'年' in date:
                    currDate.weight*=1.5
                if not formatedDate['time']=="00:00:00":
                    currDate.weight*=2.5
                if currDate.position<len(text)/2:
                    currDate.weight*=1.2
                if currDate.position<len(text)/2.5:
                    currDate.weight*=1.2
                if currDate.position<len(text)/3:
                    currDate.weight*=1.2
                if currDate.position<len(text)/3.5:
                    currDate.weight*=1.2
                if currDate.position<len(text)/4:
                    currDate.weight*=1.2
                if currDate.position<len(text)/4.5:
                    currDate.weight*=1.2
                if currDate.position < 70:
                    start = 0
                else:
                    start = currDate.position-50
                if currDate.position>len(text)-71-16:
                    end = len(text)-1
                else:
                    end = currDate.position+16+50
                currDate.htmlFragment = text[start:end]
                dateList.append(currDate)
                text=text[:pos]+length*'a'+text[pos+length:]
        return dateList
    
    def __addWeight(self, dateList, isUnicode):
        u'''
        根据权值表对日期表里的每个日期进行加权
        input：dateList----DateStruct型日期列表
        output：dateList---加权后的日期列表        
        '''
        weightList = [
            self.WeightStruct(u"来源", 2.5),
            self.WeightStruct(u"author", 2.2),
            self.WeightStruct(u"post", 2.0),
            self.WeightStruct(u"artical", 2),
            self.WeightStruct(u"发布", 1.5),
            self.WeightStruct(u"阅读", 1.5),
            self.WeightStruct(u"发表", 1.5),
            self.WeightStruct(u"date", 1.5),
            self.WeightStruct(u"pub", 1.5),
            self.WeightStruct(u"分享", 1.5),
            self.WeightStruct(u"日期", 1.2),
            self.WeightStruct(u"时间", 1.2),
            self.WeightStruct(u"count", 1.2),
            self.WeightStruct(u"Count", 1.2),
            self.WeightStruct(u"星期", 1.2),
            self.WeightStruct(u"time", 1.2),
            self.WeightStruct(u"网", 1.2),
            self.WeightStruct(u"评论", 1.2),
            ]
        if not isUnicode:
            weightList = [
                self.WeightStruct("time", 1.5),
                self.WeightStruct("issue", 2.3),
                self.WeightStruct("post", 2.0),
                self.WeightStruct("date", 1.2),
                self.WeightStruct("pub", 1.2),
                self.WeightStruct("author", 2.2),
                self.WeightStruct("count", 1.2),
                self.WeightStruct("Count", 1.2),
                self.WeightStruct("artical", 2),
            ]
        for date in dateList:
            for weightItem in weightList:
                if date.htmlFragment.find(weightItem.tag)>=0:
                    date.weight*=weightItem.weight
                    #print weightItem.tag,":",date.weight
        return dateList

    
    def __formatDate(self, date):
        u'''
        负责用正则表达式格式化日期字符串，统一成：yyyy-mm-dd
        然后调isValidDate函数检查日期是否合法，并且是否为1970-01-01到今天之间
        input：date----日期文本
        output：包括年，月，日，时间的字典
        '''
        regexp=u"((?:19)?9\d|(?:20)?[01][0-9])(?:[-\s\/.,、年]|&#24180;)([01]?[0-9])(?:[-\s\/.,、月]|&#26376;)([0-3]?[0-9])(?:日|&#26085;)?(?:\s|\\xa0){0,3}([0-2]?\d:[0-5]?\d(?::[0-5]?\d)?)?"
        item = re.search(regexp,date,re.I|re.M|re.S)
        year=item.group(1)
        month=item.group(2)
        day=item.group(3)
        time=item.group(4)
        if time:
            if time[1] == ':':
                time = "0" + time
            if len(time) == 4:
                time = time[:3] + "0" + time[3:]
            if time[4] == ':':
                time = time[:3] + "0" + time[3:]
            if len(time) == 7:
                time = time[:6] + "0" + time[6]
            if len(time)<6:
                time = time + ":00"
        else:
            time="00:00:00"
        if len(year) == 2:
            year = cur_year_2 + year
        return {'year':year,'month':month,'day':day,'time':time}

    def __isValidDate(self, date):
        u'''
        负责检查日期是否合法，并且是否为1970-01-01到今天之间
        input：date-----日期文本（yyyy-mm-dd格式）
        output：True----合法
                False---不合法        
        '''
        try:
            if date:
                dt=datetime.datetime.strptime(date,'%Y-%m-%d').date()
            if dt>datetime.date(1970,01,01) and dt<=datetime.date.today():
                return True
        except Exception as e:
            return False
        return False

    def __printResult(self, dateList):
        # for date in dateList:
        #   print date.datetime,"---------",date.weight,"---------",date.position
        # if len(dateList)>0:
        #   print dateList[0].htmlFragment
        pass
    
    def __denoise(self,html):
        try:
            html = filter_invalid_tags(html)
        except Exception as e:
            #traceback.print_exc()
            pass
        html = HTMLParser.HTMLParser().unescape(html)
        html = re.sub("\n\r", "", html)
        html = html.replace("     "," ")
        return html

def _ctime_datetime(html, url=''):
    ctime = GetDate().getDate(html, url)
    return ctime
    
if __name__ == '__main__':
    import requests
    url = 'http://www.110.com/panli/panli_48424.html'
    url = 'http://www.zyjjw.cn/news/china/2016-08-10/360176.html'
    url = 'http://www.weibo.com/p/230418638695670102wy6u'
    resp = requests.get(url)
    resp.encoding = 'utf8'
    ctime = GetDate().getDate(resp.text)
    print '-------ctime: ',  ctime
    #logging.error("fsadfasd")
