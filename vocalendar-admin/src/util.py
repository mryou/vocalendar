# coding=utf-8
'''
Created on 2012/03/06

@author: mryou
'''
import cgi
import logging
logger = logging.getLogger(__name__)

from datetime import datetime

class RequestData():
    '''
    リクエストデータを扱うクラス
    実は、cgi.FieldStrage().getValueを使った方が良いことが判明してますｗ
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
    '''
        日付に関するユーティリティー。
        まだ未使用
    '''

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
