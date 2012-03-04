# coding=utf-8

import os, sys, traceback
import gflags
import httplib2
import threading
import cgi
from datetime import *
import urllib2
from htmlentitydefs import codepoint2name

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run

prohibitionId = 'pcg8ct8ulj96ptvqhllgcc181o@group.calendar.google.com'

class RequestData():

	def __init__( self, environ ):
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

class GCalendarUser():

	def __init__( self, environ ):
		self.flow = OAuth2WebServerFlow(
		  client_id='1024985834463.apps.googleusercontent.com',
		  client_secret='MCNVyWEAXaG9fCqXcUHWvUyC',
#		  client_id='269567140900.apps.googleusercontent.com',
#		  client_secret='_wF3RvNpRyyt2k9m4dPmjkLp',
		  scope='https://www.googleapis.com/auth/calendar',
		  user_agent='vocalendar-sync/1.0.0',
#		  user_agent='vocalendar-sync-sub/1.0.0',
		  approval_prompt='force'
#		  access_type='offline'
		  )
		self.developerKey='AIzaSyDlk_D0N8F4mJIi1PvgC27jujdSAH5pJxA'
#		self.developerKey='AIzaSyCDSY-tykDOmhIBj4ZdSxHf1VIq7k9yvZE'
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

class GCalendarService():

	def __init__( self, GCalendarUser ):

		self._user = GCalendarUser
		self.service = build(serviceName='calendar', version='v3', http=self._user.http, developerKey=self._user.developerKey)

	def getCalendars(self):
		result = self.service.calendarList().list().execute()
		if result.has_key('items'):
			return result['items']
		return []

	def getCalendar(self, id):
		return GCalendar( self.service, self.service.calendars().get(calendarId=id).execute())

class GCalendar():

	def __init__(self, service, calendar):
		self.service = service
		self.calendar = calendar

	def getName(self):
		return self.calendar['summary']

	# idがあるとダメなので同期には使えない
	def create(self, event):
		event.pop('id', None)
		event.pop('organizer', None)
		event['start']['timeZone']='Asia/Tokyo'
		event['end']['timeZone']='Asia/Tokyo'

		try:
			self.service.events().insert(calendarId=self.calendar['id'], body=event).execute()
			pass
		except HttpError, e:
			print e
			pass
			raise

	def getEvent(self, eventid):
		try:
			event = self.service.events().get(calendarId=self.calendar['id'], eventId=eventid).execute()
			# わざわざpassを入れているのはdebugで↑をコメントアウトしたときにエラーにならないように(^_^;)
			pass
		except HttpError, e:
			# not found（対象無し）は無視
			if e.resp.status == 404:
				return None
			else:
				raise

		return event

	def getRecurringEvents(self, eventid):
		try:
			events = self.service.events().instances(calendarId=self.calendar['id'], eventId=eventid).execute()
			pass
		except HttpError, e:
			# not found（対象無し）は無視
			if e.resp.status == 404:
				return None
			else:
				raise
		return events

	def delete(self, eventid):

		try:
			self.service.events().delete(calendarId=self.calendar['id'], eventId=eventid).execute()
			pass
		except HttpError, e:
			# not found（対象無し） or Resource has been deleted（削除済み）は無視
			if not ( e.resp.status == 404 or e.resp.status == 410 ):
				raise

	# import_なのはimportが予約後だから。
	def import_(self, event):

		target = dict(event)
		target.pop('id', None)
		target.pop('organizer', None)
		target['start']['timeZone']='Asia/Tokyo'
		target['end']['timeZone']='Asia/Tokyo'

		try:
			self.service.events().import_(calendarId=self.calendar['id'], body=target).execute()
			return u'インポート:'
		except HttpError, e:
			# not found（対象無し） or Resource has been deleted（削除済み）は
			# The requested identifier already exists.(ID重複) or Backend Error（謎） idを削除してinsert
			#if e.resp.status == 404 or e.resp.status == 410 or e.resp.status == 409 or e.resp.status == 503:
			print event
			print e
			pass
			raise


	def getEvents(self, **arg):
		param = {
				'calendarId': self.calendar['id'],
				'timeMin': '1970-01-01T00:00:00Z',
				#'timeMax': '2039-12-31T00:00:00Z',
				'orderBy': 'updated'
				}
		param.update(arg)
		events = self.service.events().list(**param).execute()
		return events

	def getCount(self):
		count = 0
		html = u''
		events = self.getEvents()
		file = open( os.path.join(os.path.dirname(__file__) , 'alldata.csv'), 'w' )
		file.writelines('開始日\t終了日\tID\t件名\t作成者\t作成日\t更新時間\t更新回数\n')
		while events.has_key('items'):
			count += len( events.get('items') )
			for event in events.get('items'):
				file.write( ( self.toCsvString(event) + u'\n').encode('utf-8') )

			page_token = events.get('nextPageToken')
			if page_token:
				events = self.getEvents(pageToken=page_token)
			else:
				break

		html += u'</br>'
		html += u"<a href='./alldata.csv' target='_brank'>データダウンロード</a>"
		file.close()

		return count, events['updated'], html

	def deleteAll(self):

		if self.calendar['id'] == prohibitionId:
			return 0, u'このカレンダーは削除できません'

		count = 0
		html = u''
		events = self.getEvents()
		while events.has_key('items'):
			count += len( events.get('items') )

			for event in events.get('items'):
				html += self.toString(event)
				html += u'</br>'
				self.delete(event['id'])

			page_token = events.get('nextPageToken')
			if page_token:
				events = self.getEvents(pageToken=page_token)
			else:
				break
		return count, html

	def syncTo(self, dstCalendar):

		if dstCalendar.calendar['id'] == prohibitionId:
			return 0, u'このカレンダーを同期先にできません'

		dstEvents = dstCalendar.getEvents()
		lastModifiedStr = dstEvents.get('updated').split( '.' )[0].split('Z')[0]
		lastModified = datetime.strptime(lastModifiedStr, '%Y-%m-%dT%H:%M:%S')
		minUpdate = lastModified - timedelta(days=1)
		minUpdateStr = minUpdate.strftime('%Y-%m-%dT%H:%M:%SZ')
		print minUpdateStr

		count, html = self.copyTo(dstCalendar=dstCalendar, updatedMin=minUpdateStr, showDeleted=True)
		return count, html

	def copyTo(self, dstCalendar,  **fromConditions):

		if dstCalendar.calendar['id'] == prohibitionId:
			return 0, u'このカレンダーを同期先にできません'

		count = 0
		html = u''
		param = {
				'showDeleted': True
				}
		param.update(fromConditions)
		events = self.getEvents(**param)
#		file = open( os.path.join(os.path.dirname(__file__) , 'alldata.csv'), 'w' )
		while events.has_key('items'):
			for event in events.get('items'):
				count += 1
				print count
#				file.write( ( self.toCsvString(event) + u'\n').encode('utf-8') )

				if event.get('status') == 'cancelled':
					dstCalendar.delete(event.get('id'))
					html += u'削除:' + self.toString(event)
					html += u'</br>'
					continue

				resultstr = dstCalendar.import_(event)
				html += resultstr + self.toString(event)
				html += u'</br>'

			page_token = events.get('nextPageToken')
			if page_token:
				param['pageToken'] = page_token
				events = self.getEvents(**param)
			else:
				break

#		html += u'</br>'
#		html = u"<a href='./alldata.csv' target='_brank'>データダウンロード</a>"
#		file.close()

		return count, html

	def toString(self, event):

		if event.get('start') is None:
			return u'詳細不明 id: ' + event.get('id')

		eventdate = event.get('start').get('date')
		if not event.get('start').has_key('date'):
			eventdate = event.get('start').get('dateTime')
		summary = event.get('summary')
		if summary is None:
			summary = u'(ブランク)'
		return event.get('status') + u':' + event.get('updated') + u':'+ eventdate + u':' + summary

	def toCsvString(self, event):
		if event.get('start') is None:
			return u'詳細なし id: ' + event.get('id')

		startdate = event.get('start').get('date')
		if not event.get('start').has_key('date'):
			startdate = event.get('start').get('dateTime')

		enddate = event.get('end').get('date')
		if not event.get('end').has_key('date'):
			enddate = event.get('end').get('dateTime')

		summary = event.get('summary')
		if summary is None:
			summary = u'(ブランク)'

		csv = u''
		csv += startdate
		csv += u'\t'
		csv += enddate
		csv += u'\t'
		csv += event.get('id')
		csv += u'\t'
		csv += summary
		csv += u'\t'
		csv += event.get('creator').get('email')
		csv += u'\t'
		csv += event.get('created')
		csv += u'\t'
		csv += event.get('updated')
		csv += u'\t'
		csv += str(event.get('sequence'))

		return csv


def application(environ, start_response):

	print '----------- start ----------'
	request = RequestData(environ)
	user = GCalendarUser(environ)

	if not user.isVailedCredentials() or request.method == 'GET':
		print 'Credentials is None'
		if request.method == 'GET':
			if len(request.query) == 0:
				start_response('301 Moved', [('Location', user.authorize_url)])
				return ['',]
			else:
				user.getAccessToken(request)

	try:
		user.authorize()
		service = GCalendarService(user)
		calendars = service.getCalendars()
	except Exception, e:
		print e
		start_response('200 OK', [('Content-type', 'text/html')])
		return buildUI([], str(e).replace('<','').replace('>','') )


	if request.method == 'GET':
		start_response('200 OK', [('Content-type', 'text/html')])
		return buildUI(calendars)

	response = u''
	try:
		if request.params.has_key('delete'):
			calendar = service.getCalendar( request.params.get('deleteid') )
			count, html = calendar.deleteAll()
			response += calendar.getName() + u'<br>'
			response += u'削除件数 ' + str(count) + u'<br>'
			response += u'<p>削除データ</p>'
			response += html
		if request.params.has_key('sync'):
			calendar = service.getCalendar( request.params.get('syncsrcid') )
			count, html = calendar.syncTo( service.getCalendar(request.params.get('syncdstid')) )
			response += u'同期件数 ' + str(count) + u'<br>'
			response += u'<p>同期データ</p>'
			response += html
		if request.params.has_key('insert'):
			calendar = service.getCalendar( request.params.get('copysrcid') )
			count, html = calendar.copyTo( service.getCalendar(request.params.get('copydstid')) )
			response += u'コピー件数 ' + str(count) + u'<br>'
			response += u'<p>コピーデータ</p>'
			response += html
		if request.params.has_key('count'):
			calendar = service.getCalendar( request.params['calendarid'] )
			count, lastmodified, html = calendar.getCount()
			response += calendar.getName() + u'<br>'
			response += u'件数 ' + str(count) + u'<br>'
			response += u'最終更新日時(UTC)： ' + lastmodified
			response += html
	except Exception, e:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		traceback.extract_tb(exc_traceback)
		response += str(e)

	start_response('200 OK', [('Content-type', 'text/html')])
	return buildUI(calendars, response)

def buildUI(calendars, *addHtmls):

	html = u'''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Vocalendar Admin</title>
</head>
<body>
<h1>Vocalendar 管理画面</h1>
<form method='post'>
<h2>件数取得</h2>
<select name='calendarid'>
'''
	for calendar in calendars:
		html += u"<option value='" + calendar['id'] + u"'>" + calendar['summary'] + u"</option><br>"

	html += u'''
</select>
<input type='submit' name='count' value='件数取得'>
<h2>差分同期</h2>
<p>同期先の最終更新日時（最後に同期orインポートした時刻）より1日前のデータから同期。</p>
同期元<select name='syncsrcid'>
'''
	for calendar in calendars:
		html += u"<option value='" + calendar['id'] + u"'>" + calendar['summary'] + u"</option><br>"

	html += u'''
</select>
同期先<select name='syncdstid'>
'''
	for calendar in calendars:
		if calendar['id'] == prohibitionId:
			continue
		html += u"<option value='" + calendar['id'] + u"'>" + calendar['summary'] + u"</option><br>"

	html += u'''
</select>
<input type='submit' name='sync' value='同期'>
<!--
<h2>全件削除（危険(；´Д`)） </h2>
<select name='deleteid'>
'''
	for calendar in calendars:
		if calendar['id'] == prohibitionId:
			continue
		html += u"<option value='" + calendar['id'] + u"'>" + calendar['summary'] + u"</option><br>"

	html += u'''
</select>
<input type='submit' name='delete' value='全件削除'>
-->
<h2>全件同期</h2>
コピー元<select name='copysrcid'>
'''
	for calendar in calendars:
		html += u"<option value='" + calendar['id'] + u"'>" + calendar['summary'] + u"</option><br>"

	html += u'''
</select>
コピー先<select name='copydstid'>
'''
	for calendar in calendars:
		if calendar['id'] == prohibitionId:
			continue
		html += u"<option value='" + calendar['id'] + u"'>" + calendar['summary'] + u"</option><br>"

	html += u'''
</select>
<input type='submit' name='insert' value='コピー'>
</form>
<h2>結果</h2>
'''
	for addhtml in addHtmls:
		html += addhtml

	html += u'</html>'
	print '----------------------'
	return html.encode('utf-8')
