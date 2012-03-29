# coding=utf-8
'''
Created on 2012/03/06

@author: mryou
'''
import cgi
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from datetime import datetime

class RequestData():
    '''
    リクエストデータを扱うクラス
    '''


    def __init__(self, environ):
        '''
        コンストラクタ
        @param : environ Applicationのリクエストデータ
        '''
        self.method = environ.get('REQUEST_METHOD')
        self.query = cgi.parse_qsl(environ.get('QUERY_STRING'))
        self.params = {}
        if self.method == 'POST':
            wsgi_input     = environ['wsgi.input']
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            self.query = cgi.parse_qsl(wsgi_input.read(content_length))

        for param in self.query:
            key, value = param
            self.params[key] = value
        logger.debug(self.method)
        logger.debug(self.params)


class DateUtil():

    def __init__(self):
        pass

    def confStr2DateTime(self, dateStr):
        try:
            return datetime.strptime(dateStr, '%Y-%m-%dT%H:%M:%S')
        except ValueError, e:
            pass

        try:
            return datetime.strptime(dateStr, '%Y-%m-%d')
        except ValueError, e:
            pass
