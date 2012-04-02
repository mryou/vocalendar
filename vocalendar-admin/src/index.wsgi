# coding=utf-8

import os, sys, traceback
import gflags
import httplib2
import threading
import cgi
import urllib2
import logging
import cgitb
import codecs

from htmlentitydefs import codepoint2name

sys.path.append(os.path.dirname(__file__))
import gCalClient.GCalendarAuth
import gCalClient.GCalendar
import util

# ログの設定。何故か日本語がasciiエンコーディングになる。
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
sys.stdout = codecs.getwriter('utf_8')(sys.stdout)
sys.stderr = codecs.getwriter('utf_8')(sys.stderr)
# 画面にTraceBackを出してくれるらしいが出ない・・・。
cgitb.enable()

prohibitionId = 'pcg8ct8ulj96ptvqhllgcc181o@group.calendar.google.com'

def application(environ, start_response):

	logger.debug( u'----------- start ----------' )
	request = util.RequestData(environ)
	auth = gCalClient.GCalendarAuth.GCalendarAuth(environ)

	if not auth.isVailedCredentials() or request.method == 'GET':
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
		targetCalendar = service.getCalendar(prohibitionId)
		eventColors = targetCalendar.getEventColor()
	except Exception, e:
		type, value, tb = sys.exc_info()
		tblist = traceback.format_exception(type, value, tb)
		for tb in tblist:
			logger.debug(tb)
			response += tb
		start_response('200 OK', [('Content-type', 'text/html')])
		return buildUI([], {}, response )


	if request.method == 'GET':
		start_response('200 OK', [('Content-type', 'text/html')])
		return buildUI(calendars, eventColors)

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
			count, delcount, html = calendar.syncTo( service.getCalendar(request.params.get('syncdstid')), request.params.get('syncAllData') )
			response += u'同期件数 ' + str(count) + u' 件 '
			response += u'(内削除データ ' + str(delcount) + u' 件)<br>'
			response += u'<p>同期データ</p>'
			response += html

		if request.params.has_key('cancel'):
			calendar = service.getCalendar( request.params.get('canceldstid') )
			count, delcount, html = calendar.cancelDelete()
			response += u'全体件数 ' + str(count) + u' 件 '
			response += u'(内復活データ ' + str(delcount) + u' 件)<br>'
			response += u'<p>復活データ</p>'
			response += html

		if request.params.has_key('chColor'):
			calendar = service.getCalendar( request.params.get('coldstid') )
			count, html = calendar.changeEventColor( request.params.get('colSearchStr'), request.params.get('colorid') )
			response += u'変更件数 ' + str(count) + u' 件 '
			response += u'<p>変更データ</p>'
			response += html

		if request.params.has_key('count'):
			calendar = service.getCalendar( request.params['calendarid'] )
			ount, lastmodified, html = calendar.getCount( request.params.get('description'), request.params.get('onlyDelData') )
			response += calendar.getName() + u'<br>'
			response += u'件数 ' + str(count) + u' 件<br>'
			response += u'最終更新日時(UTC)： ' + lastmodified
			response += html
	except Exception, e:
		type, value, tb = sys.exc_info()
		tblist = traceback.format_exception(type, value, tb)
		for tb in tblist:
			logger.debug(tb.encode('utf-8'))
			response += tb
#		raise


	start_response('200 OK', [('Content-type', 'text/html')])
	return buildUI(calendars, eventColors, response)

def buildUI(calendars, eventColors, *addHtmls):

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
<input type='checkbox' id='description' name='description' value='True' /><label for='description'>DLデータに詳細を含める</label>
<input type='checkbox' id='onlyDelData' name='onlyDelData' value='True' /><label for='onlyDelData'>削除データのみ</br></label>
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
		if not calendar['editable']:
			continue
		html += u"<option value='" + calendar['id'] + u"'>" + calendar['summary'] + u"</option><br>"

	html += u'''
</select>
<input type='checkbox' name='syncAllData' value='True' /> 差分ではなく全件同期する</br>
<input type='submit' name='sync' value='同期'>

<h2>カラー変更</h2>
対象<select name='coldstid'>
'''
	for calendar in calendars:
		html += u"<option value='" + calendar['id'] + u"'>" + calendar['summary'] + u"</option><br>"

	html += u'''
</select>
検索文字列<input type='text' name='colSearchStr' /><br>
<input type='radio' name='colorid' value='' >基本色
'''
	for id, color in eventColors.iteritems():
		html += u"<input type='radio' name='colorid' value='" + id + u"' /><span style='color:" + color['background'] + u"'>■</span>"


	html += u'''
<br>
<input type='submit' name='chColor' value='変更'>

<!--
<h2>削除復活</h2>
対象<select name='canceldstid'>
'''
	for calendar in calendars:
		html += u"<option value='" + calendar['id'] + u"'>" + calendar['summary'] + u"</option><br>"

	html += u'''
</select>
<br>
<input type='submit' name='cancel' value='変更'>
-->
</form>

<h2>結果</h2>
'''
	for addhtml in addHtmls:
		html += addhtml

	html += u'</html>'
	logger.debug( '----------------------' )
	return html.encode('utf-8')
