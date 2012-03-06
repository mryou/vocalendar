'''
Created on 2012/03/06

@author: tonomura
'''
import cgi

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
        print self.method
        print self.params