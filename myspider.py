import sys
sys.path.append('/usr/local/lib/python3.7/dist-packages/mymodule/')
import re
import json
import requests
from time import time
from lxml import etree
from urllib import parse
from requests import get,post,ConnectTimeout
from copy import deepcopy as dc
from pprint import pprint
from dialy import Log
logger=Log(__name__)

class Spider():
    
    default_header={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36'}
    default_proxy={"http": "socks5://127.0.0.1:22230","https": "socks5://127.0.0.1:22230"}
    
    def __init__(self,url,headers=None):
        self.url=url
        if type(headers)==str:
            self.headers=Spider._get_header(headers)
        elif type(headers)==dict:
            self.headers=headers.copy()
        elif not headers:
            self.headers=Spider.default_header.copy()
        else:raise ValueError('Unexpected type -> %s'%type(headers))
        if not self.headers.get('User-Agent'):self.headers.update(Spider.default_header)
        
    @staticmethod
    def _get_time(n=13):
        return str(time()).replace('.','')[:n]
    
    @staticmethod
    def _del_attr(dic,pattern_del):
        for x in pattern_del.split():
            del(dic[x])
            print('del->',x)

    @staticmethod
    def _get_header(str_in,pattern_del=''):
        str_in=str_in.replace('\t','')
        dic=eval('{'+re.sub('[ \t]*(.+?): *(.*)',r'"\1":"\2",',str_in)+'}')
        Spider._del_attr(dic,pattern_del)
        return dic
    
    @staticmethod
    def _get_data(str_in, p_in='', debug=0):
        if str_in.startswith('http'):str_in=re.sub('(http.+?\?)','',str_in)
        str_in=re.sub('&[^=]+?&','&',str_in)
        result=eval(('{'+re.sub('([^&]+)=([^&]*)',r'"\1":"\2",',str_in)+'}').replace('&',''))
        Spider._del_attr(result, p_in)
        if debug:pprint(result)
        return result

    @staticmethod
    def _transform_cookie_to_str(dict_cookie):
        str_cookie=''
        for x in dict_cookie.items():
            str_cookie+=x[0]+'='+str(x[1])+';'
        return str_cookie
    @staticmethod
    def _transform_cookie_to_dict(str_cookie):
        return dict([x.split('=') for x in str_cookie.replace(' ','').split(';') if x])

    @staticmethod
    def _get_chinese_char(s):
        return re.findall('[\u4e00-\u9fa5]+',s)
    @staticmethod
    def _get_xpath(r):
        return etree.HTML(r.text)
    
    @staticmethod
    def compare_params(urls_t, n=''):
        t={}
        if type(urls_t==str):urls_t=[Spider.get_data_(x) for x in urls_t]
        for i,dic in enumerate(urls_t):
            for k in dic:
                try:
                    if i==0:t[k]=[dic[k]]
                    else:
                        if dic[k] not in t[k]:t[k].append(dic[k])
                except:
                    print('The index %s have key: %s'%(i,k))
        for k in t:
            if len(t[k])!=1:
                print(k,'=')
                print(t[k])
                print('-'*10)

    @staticmethod
    def _update_cookie(header,c_dict):
        cookie=Spider._transform_cookie_to_dict(header['Cookie'])
        cookie.update(c_dict)
        header['Cookie']=Spider._transform_cookie_to_str(cookie)
        
    def get_data(self,p_in=''):
        return Spider._get_data(self.url,p_in)
    
    def get_time(self, n):
        return Spider._get_time(n)



    def set_attribute(self,data,key, value, return_=1):
        data[key]=value
        if return_:return data
        
    def set_header(self,headers):
        self.headers=headers if type(headers)==dict else Spider.get_header_(headers)

    def set_url(self, params, url_encode=0):
        self.url=self.url+'?'+(parse.urlencode(params))

    def update_cookie(self,c_dict):
        cookie=Spider._transform_cookie_to_dict(self.headers['Cookie'])
        cookie.update(c_dict)
        self.headers['Cookie']=Spider._transform_cookie_to_str(cookie)
    
    
                
    def get(self,is_post=0,*args,timeout=5,use_proxy=0,proxy=None,need_new_cookie=0,
            no_warning_new_cookie=0,update_cookie_immediately=0,**kw):
        
        proxies=proxy or (Spider.default_proxy if use_proxy else {})
        try:
            r=get(self.url,headers=self.headers, *args,timeout=timeout,proxies=proxies,**kw) if \
               not is_post else post(self.url,headers=self.headers, *args,
                                     timeout=timeout,proxies=proxies,**kw)
            if r.status_code!=200:
                logger.warning('There may be an exception here ,because the status_code is %s'%r.status_code)

            new_cookie=dict(r.cookies)
            if new_cookie and not (need_new_cookie or no_warning_new_cookie or update_cookie_immediately):
                logger.warning('Notes that the cookie should be update,because this new cookie generated: %s'%str(new_cookie),
                            stack_info=True)
            if update_cookie_immediately and new_cookie:self.update_cookie(new_cookie)

            return r if not need_new_cookie or update_cookie_immediately else [r,new_cookie]
        
        except ConnectTimeout as e:
            logger.error('Timeout while get %s'%self.url)
##            raise e
