#coding=utf-8

import os,sys
try:
    import httplib2  
except ImportError as e:
    os.system('pip install -U httplib2')
    import httplib2
try:
    from bs4 import BeautifulSoup
except ImportError as e:
    os.system('pip install -U beautifulsoup4')
    from bs4 import BeautifulSoup
from urllib.parse import urlencode  
import re
import logging
import smtplib  
from email.mime.text import MIMEText  
 
log_file = os.path.join(os.getcwd(),'checkLinks.csv')
log_format = '[%(asctime)s] [%(levelname)s] %(message)s'
logging.basicConfig(format=log_format,filename=log_file,filemode='w',level=logging.DEBUG)
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter(log_format)
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

#获取页面链接列表
def getURL(url,session=None):
    urlLinks = []
    resLinks = []
    linkTypes = {'a':'href','iframe':'src','img':'src','script':'src','link':'href'}
    urlParse = url.split('/')
    rootURL = urlParse[0] + '//' + urlParse[2] #只需要/之前的和/之后的部分，只需要根链接
    if session is None:
        headers = {'contentType':'text/html;charset=UTF-8',
                   'Cache-Control':'no-cache',
                   'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.4 Safari/537.36'}#认为不需要登陆
    else:
        headers = {'contentType':'text/html;charset=UTF-8',
                   'Cache-Control':'no-cache',
                   'Cookie':'session=' + session,#不为空，认为需要登陆，保存头文件
                   'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.4 Safari/537.36'}
    http = httplib2.Http() 
    try:
        response, content = http.request(url, 'GET', headers=headers)#尝试链接到url，尝试登陆
    except Exception as e:
        logging.error(str(e) + ', ' + url) #报错，输出页面
        return 5001,url       #返回5001和url
    if response.status == 200:
        try:
            soup = BeautifulSoup(str(content),'html.parser',from_encoding='utf-8') #json解析器
            #获取所有页面链接
            for linkType in linkTypes:         #字典名
                for links in soup.find_all(linkType):        #正则匹配所有<linkType>中间的内容，构建列表，依次选中
                    if links is not None:                    #找到了<linkType>标记的部分
                        link = links.get(linkTypes[linkType])       #获取标签中属性为类似：<a> 'href'= some  <a> 中的some  获取href,src,src,src,href作为链接
                        if link is not None and link != '' and link != '/' and not link.find('t_=') > 0:    #some有意义，链接有意义
                            if re.search(r'^(\\\'|\\")',link):                #以下为用正则得到页面里正确，完整的符合要的标签中中属性的链接
                                link = link[2:-2] 
                            if re.search(r'/$',link): 
                                link = link[:-1]
                            if re.search(r'^(http://.|https://.)',link):
                                if linkType in ['a','iframe']:
                                    urlLinks.append((link,url)) 
                                else:
                                    resLinks.append((link,url))
                            elif re.search(r'^(//)',link):
                                link = urlParse[0] + link
                                if linkType in ['a','iframe']:
                                    urlLinks.append((link,url))
                                else:
                                    resLinks.append((link,url))
                            elif re.search(r'^/',link):
                                link = rootURL + link
                                if linkType in ['a','iframe']:
                                    urlLinks.append((link,url))
                                else:
                                    resLinks.append((link,url))
                            elif re.search(r'^(../)',link):
                                step = link.count('../')
                                link = link.replace('../','')
                                upStep = step - (len(urlParse)-4)    #根链接补全，或者用urlparse补全
                                if upStep >= 0:
                                    link = rootURL  + '/' + link
                                else:
                                    upStep = (len(urlParse)-4) - step
                                    linkTemp = ''
                                    for linkTmp in urlParse[3:-(upStep+1)]:
                                        linkTemp = linkTemp + '/' + linkTmp
                                    link = rootURL + linkTemp + '/' + link
                                if linkType in ['a','iframe']:
                                    urlLinks.append((link,url))
                                else:
                                    resLinks.append((link,url))
                            elif not re.search(r'(:|#)',link):
                                link = url + '/' + link
                                if linkType in ['a','iframe']:
                                    urlLinks.append((link,url))
                                else:
                                    resLinks.append((link,url))
                            print(link)
            return response.status,{'urlLinks':urlLinks,'resLinks':resLinks} #将两个列表以字典的形式返回，正常返回
        except Exception as e:
            logging.error(str(e) + ', ' + url)
            return 5001,url 
    return response.status,url

#检查链接
def checkLink(url,session=None):
    if session is None:
        headers = {'contentType':'text/html;charset=UTF-8',
                   'Cache-Control':'no-cache',
                   'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.4 Safari/537.36'}
    else:
        headers = {'contentType':'text/html;charset=UTF-8',
                   'Cache-Control':'no-cache',
                   'Cookie':'session=' + session,
                   'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.4 Safari/537.36'}
    http = httplib2.Http()
    try:
        response, content = http.request(url[0], 'GET', headers=headers) #url[0]是子链接
    except Exception as e: #看request能不能工作，不工作报错
        logging.error(str(e) + ', ' + url[0] + ', ' + url[1])
        return 5001,url
    if response.status == 200: 
        logging.info(str(response.status) + ', ' + url[0] + ', ' + url[1])
    else:
        logging.error('[ ' + str(response.status) + ' ], ' + url[0] + ', ' + url[1])    #状态不等于两百，输出
    return response.status,url

#链接分类 过滤掉站外链接
def classifyLinks(urlList,baseURL,checkList,checkedList,checkNext):
    for linkType in urlList:              
        if len(urlList[linkType]) > 0:                #如果这类链接列表中有元素
            for link in urlList[linkType]:
                inCheck = False
                for i in range(len(checkList)):
                    if link[0] in checkList[i]:     
                        inCheck = True   
                        break
                if link[0].split('/')[2].find(baseURL) > 0 and not inCheck and link[0] not in checkedList: 
                                                #如果link[0]不在checkList中，并且link[0]是原始页面的子孙并且也不在已检测链接里
                    checkList.append(link)     #那么将link放入checklist中
                    if linkType == 'urlLinks':   
                        checkNext.append(link)
    return checkList,checkNext

#获取登录Session
def getSession(url, postData):
    headers = {'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
               'X-Requested-With':'XMLHttpRequest',
               'Cache-Control':'no-cache',
               'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.4 Safari/537.36'}#反爬虫
    http = httplib2.Http()
    response, content = http.request(url, 'POST', urlencode(postData), headers=headers)#response为返回的状态，200.404之类的，content是网页的json数据
    if response.status == 200:
        match = re.search(r'true,"message":"(\w*)"',str(content))#str(content）变为字符串，匹配true，“message”：字母数字下划线，匹配到之后存下来，存在match里
        if match is not None:
            session = match.group(1)
            return response.status,session #返回状态和session
        else:
            return 0,str(content) # 返回0，和字符串
    else:
        return response.status,str(content) 

def main():
    homePage = 'http://g.yeeyan.org' #首页链接
    urlParse = homePage.split('/') 
    baseURL = urlParse[2][len(urlParse[2].split('.')[0])+1:] 
    checkList = []
    checkedList = []
    checkNext = []
    errorLinks = []
    pageNum = 0
    ifLogin = 0 #是否登录开关 ，是否需要登录
    session = None #会话
    if ifLogin:
        loginUrl = homePage + '/admin/user/login' #登陆页面
        postData = {'username':'username@zreading.com',
                    'password':'password',
                    'remeber':'0'} #用户名，密码，要不要记住密码
        status,session = getSession(loginUrl,postData)
        if status != 200:
            logging.error(session)
            session = None
    status,urlList = getURL(homePage,session)   #获取页面上符合要求所有链接
    if status == 200:
        checkList,checkNext = classifyLinks(urlList,baseURL,checkList,checkedList,checkNext)#第一次时，checklist为页面中所有根节点相同的不含下一层连接的子页面，check next含有下一层链接的子链接
        while True:
            if len(checkList) > 0:     #有需要检测的'resLinks'
                pageNum += 1           #记录检测的链接层数
                logging.info('开始检查第 ' + str(pageNum) + ' 层链接')
                if ifLogin:
                    status,session = getSession(loginUrl,postData)
                    if status != 200:
                        logging.error(session)
                        session = None
                for link in checkList:
                    status,url = checkLink(link,session) #url，二维链接列表，包含子链接和父链接
                    if status != 200:
                        errorLinks.append((status,url))
                    checkedList.append(link[0])
                del checkList[:] #检查完删掉checklist中的内容，清空checklist；
            if len(checkNext) > 0: #有需要检测的'urlLinks'
                checkNextN = []
                if ifLogin:
                    status,session = getSession(loginUrl,postData)  #session str(content)或者\w*
                    if status != 200:
                        logging.error(session)
                        session = None
                for link in checkNext: 
                    status,urlList = getURL(link[0],session)    #令status，urllist等于getURL(link[0],session)这个函数的输出， #获取'resLinks'链接中页面上符合要求所有链接，看到这里，猜测'resLinks'是一个拥有子页面的的链接类型
                    if status == 200:
                        checkList,checkNextN = classifyLinks(urlList,baseURL,checkList,checkedList,checkNextN)
                    else:
                        logging.error('[ ' + str(status) + ' ] ' + urlList)
                checkNext = checkNextN
            else:
                logging.info('链接检查完毕，共检查 ' + str(len(checkedList)) + ' 个链接，其中有 ' + str(len(errorLinks)) + ' 个异常链接')
                break
        if len(errorLinks) > 0:
            text = '<html><body><p>共检查 ' + str(len(checkedList)) + ' 个链接，其中有 ' + str(len(errorLinks)) + ' 个异常链接，列表如下：' + '</p><table><tr><th>Http Code</th><th>Url</th><th>Referer Url</th></tr>'
            for link in errorLinks:
                text = text + '<tr><td>' + str(link[0]) + '</td><td>' + link[1][0] + '</td><td>' + link[1][1] + '</td></tr>'
            text = text + '</table></body></html>'
            #sendMail(text)
    else:
        logging.error('[ ' + str(status) + ' ] ' + urlList)
    
if __name__ == '__main__':
    main()
