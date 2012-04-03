# coding=utf-8
'''
Created on 2012/03/06

@author: mryou
'''
import os
import httplib2
import logging

logger = logging.getLogger(__name__)

from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow

class GCalendarAuth():
    '''
    Google oAuth認証を扱うクラス
    '''

    def __init__( self, environ ):
        '''
        Constructor
        @param : environ Applicationのリクエストデータ
        '''
        self.flow = OAuth2WebServerFlow(
#          client_id='1024985834463.apps.googleusercontent.com',
#          client_secret='MCNVyWEAXaG9fCqXcUHWvUyC',
          client_id='269567140900.apps.googleusercontent.com',
          client_secret='_wF3RvNpRyyt2k9m4dPmjkLp',
          scope='https://www.googleapis.com/auth/calendar',
#          user_agent='vocalendar-sync/1.0.0',
          user_agent='vocalendar-sync-sub/1.0.0'
#          approval_prompt='force'
#          access_type='offline'
          )
#        self.developerKey='AIzaSyDlk_D0N8F4mJIi1PvgC27jujdSAH5pJxA'
        self.developerKey='AIzaSyCDSY-tykDOmhIBj4ZdSxHf1VIq7k9yvZE'
#        self.authorize_url = self.flow.step1_get_authorize_url('http://www.ryou.bne.jp/vocalendar-admin/')
        self.authorize_url = self.flow.step1_get_authorize_url('http://www.ryou.bne.jp/vocalendar-admin-sub/')
        logger.debug(self.authorize_url)
        self.storage = Storage( os.path.join(os.path.dirname(__file__), 'calendar.dat') )
        self.credentials = self.storage.get()

    def isVailedCredentials(self):
        '''
            保存されている認証情報が有効性を確認
        '''
        return self.credentials is not None and not self.credentials.access_token_expired

    def getAccessToken(self, request):
        '''
            oAuth認証ステップ2 codeからアクセストークンを取得
            @param : request : util.RequestDataのインスタンス
        '''
        credential = self.flow.step2_exchange(request.params['code'])
        self._save(credential)
        self.credentials = credential

    def authorize(self):
        '''
            アクセストークンで認証？
        '''
        self.http = self.credentials.authorize(httplib2.Http())


    def _save(self, credential):
        '''
            認証情報の保存
        '''
        self.storage.put(credential)
        credential.set_store(self.storage)

