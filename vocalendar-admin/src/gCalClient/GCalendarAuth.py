'''
Created on 2012/03/06

@author: tonomura
'''
import os
import httplib2

from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow

class GCalendarAuth():
    '''
    classdocs
    '''

    def __init__( self, environ ):
        '''
        Constructor
        '''
        self.flow = OAuth2WebServerFlow(
          client_id='1024985834463.apps.googleusercontent.com',
          client_secret='MCNVyWEAXaG9fCqXcUHWvUyC',
#          client_id='269567140900.apps.googleusercontent.com',
#          client_secret='_wF3RvNpRyyt2k9m4dPmjkLp',
          scope='https://www.googleapis.com/auth/calendar',
          user_agent='vocalendar-sync/1.0.0',
#          user_agent='vocalendar-sync-sub/1.0.0',
          approval_prompt='force'
#          access_type='offline'
          )
        self.developerKey='AIzaSyDlk_D0N8F4mJIi1PvgC27jujdSAH5pJxA'
#        self.developerKey='AIzaSyCDSY-tykDOmhIBj4ZdSxHf1VIq7k9yvZE'
        self.authorize_url = self.flow.step1_get_authorize_url('http://www.ryou.bne.jp/vocalendar-admin/')
        print self.authorize_url
        #self.authorize_url = self.flow.step1_get_authorize_url('http://www.ryou.bne.jp/vocalendar-admin/sub/')
        self.storage = Storage( os.path.join(os.path.dirname(__file__), 'calendar.dat') )
        self.credentials = self.storage.get()

    def isVailedCredentials(self):
        return self.credentials is None or self.credentials.invalid == True

    def getAccessToken(self, request):
        self.credentials = self.flow.step2_exchange(request.params['code'])
        self.save()

    def save(self):
        self.credentials.set_store(self.storage)
        self.storage.put(self.credentials)

    def authorize(self):
        self.http = self.credentials.authorize(httplib2.Http())
