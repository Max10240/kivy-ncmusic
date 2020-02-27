import cookielib
import urllib2

def cookies():
    """保存cookies到变量
    """
    #声明一个CookieJar对象实例来保存cookie
    cookie = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
    #此处的open方法同urllib2的urlopen方法，也可以传入request
    response = opener.open('http://example.webscraping.com')
    for item in cookie:
        print ('Name = '+item.name)
        print ('Value = '+item.value)

def save_cookies_Moz():
    """保存cookies到文件 —— Netscape格式
    """
    filename = 'cookies_Moz.txt'
    cookie = cookielib.MozillaCookieJar(filename)
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
    response = opener.open("http://example.webscraping.com")
    cookie.save(ignore_discard=True, ignore_expires=True)       # 这里必须将参数置为True，否则写入文件失败

def save_cookies_LWP():
    """保存cookies到文件 —— LWP格式
    """
    filename = 'cookies_LWP.txt'
    cookie = cookielib.LWPCookieJar(filename)
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
    response = opener.open("http://example.webscraping.com")
    cookie.save(ignore_discard=True, ignore_expires=True)       # 这里必须将参数置为True，否则写入文件失败
