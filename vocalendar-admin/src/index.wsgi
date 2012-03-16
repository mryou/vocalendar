# coding=utf-8

import os, sys, traceback
import gflags
import httplib2
import threading
import cgi
import urllib2

from htmlentitydefs import codepoint2name

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
sys.path.append(os.path.dirname(__file__))
import gCalClient.GCalendarAuth
import gCalClient.GCalendar
import util

prohibitionId = 'pcg8ct8ulj96ptvqhllgcc181o@group.calendar.google.com'

def application(environ, start_response):

	print '----------- start ----------'
	request = util.RequestData(environ)
	auth = gCalClient.GCalendarAuth.GCalendarAuth(environ)

	if not auth.isVailedCredentials() or request.method == 'GET':
		print 'Credentials is None'
		if request.method == 'GET':
			if len(request.query) == 0:
				start_response('301 Moved', [('Location', auth.authorize_url)])
				return ['',]
			else:
				auth.getAccessToken(request)

	try:
		auth.authorize()
		service = gCalClient.GCalendar.GCalendarService(auth, prohibitionId)
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
			count, delcount, html = calendar.syncTo( service.getCalendar(request.params.get('syncdstid')) )
			response += u'同期件数 ' + str(count) + u' 件 '
			response += u'(内削除データ ' + str(delcount) + u' 件)<br>'
			response += u'<p>同期データ</p>'
			response += html
		if request.params.has_key('insert'):
			calendar = service.getCalendar( request.params.get('copysrcid') )
			count, delcount, html = calendar.copyTo( service.getCalendar(request.params.get('copydstid')) )
			response += u'コピー件数 ' + str(count) + u' 件 '
			response += u'(内削除データ ' + str(delcount) + u' 件)<br>'
			response += html
		if request.params.has_key('count'):
			calendar = service.getCalendar( request.params['calendarid'] )
			count, lastmodified, html = calendar.getCount()
			response += calendar.getName() + u'<br>'
			response += u'件数 ' + str(count) + u' 件<br>'
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
		# 判定が逆なのに動いてるorz 設定時ミスしてる
		if not calendar['editable']:
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
		if not calendar['editable']:
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
		if not calendar['editable']:
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
