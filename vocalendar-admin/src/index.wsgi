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
from datetime import timedelta

# ログの設定。何故か日本語がasciiエンコーディングになる。
sys.stdout = codecs.getwriter('utf_8')(sys.stdout)
sys.stderr = codecs.getwriter('utf_8')(sys.stderr)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logger.getEffectiveLevel())
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
# 画面にTraceBackを出してくれるらしいが出ない・・・。
cgitb.enable()

sys.path.append(os.path.dirname(__file__))
import gCalClient.GCalendarAuth
import gCalClient.GCalendar
import util

prohibitionId = 'pcg8ct8ulj96ptvqhllgcc181o@group.calendar.google.com'

def application(environ, start_response):

	logger.debug( u'----------- start ----------' )

	# リクエスト前処理
	request = util.RequestData(environ)
	auth = gCalClient.GCalendarAuth.GCalendarAuth(environ)

	# 必要ならGoogleにoAuth認証を行う。

	try:
		refresh_result = auth.refresh()
	except Exception, e:
		type, value, tb = sys.exc_info()
		tblist = traceback.format_exception(type, value, tb)
		for tb in tblist:
			logger.debug(tb)

	logger.debug('reflesh result is ' + str( refresh_result ))
	logger.debug('Credentials is ' + str(auth.isVailedCredentials()) )
	if not refresh_result:
		if not auth.isVailedCredentials():# or request.method == 'GET':
			if request.method == 'GET':
				logger.debug(len(request.query))
				if len(request.query) == 0:
					logger.debug(auth.authorize_url)
					start_response('301 Moved', [('Location', auth.authorize_url)])
					return ['',]
				else:
					auth.getAccessToken(request)

	try:
		# 有効な認証かを確認？
		auth.authorize()
		service = gCalClient.GCalendar.GCalendarService(auth, prohibitionId)
	except Exception, e:
		type, value, tb = sys.exc_info()
		tblist = traceback.format_exception(type, value, tb)
		for tb in tblist:
			logger.debug(tb)
			response = tb
		start_response('200 OK', [('Content-type', 'text/html')])
		return buildUI([], {}, response )

	# 初期処理
	calendars = service.getCalendars()
	targetCalendar = service.getCalendar(prohibitionId)
	eventColors = targetCalendar.getEventColor()

	# 最初のアクセスは画面を生成するだけ
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
			count, delcount, html = calendar.syncTo( service.getCalendar(request.params.get('syncdstid')), timedelta(days=1) ,request.params.get('syncAllData') )
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
			count, lastmodified, html = calendar.getCount( request.params.get('description'), request.params.get('onlyDelData') )
			response += calendar.getName() + u'<br>'
			response += u'件数 ' + str(count) + u' 件<br>'
			response += u'最終更新日時(UTC)： ' + lastmodified
			response += html

		if request.params.has_key('saveAuth'):
			auth.save4batch()
			response += u'保存されました。'

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
	'''
	 画面生成処理。
	 MVCのV
	 @param calendars: プルダウン用カレンダー一覧
	 @param eventColors: イベントのカラー一覧
	 @param addHtmls: 結果表示用のHTML文字列

	'''
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
		if calendar['id'] == prohibitionId:
			html += u"<option value='" + calendar['id'] + u"'>" + calendar['summary'] + u"</option><br>"

	html += u'''
</select>
同期先<select name='syncdstid'>
'''
	for calendar in calendars:
		if calendar['id'] == '0mprpb041vjq02lk80vtu6ajgo@group.calendar.google.com':
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

<h2>バッチ用認証保存</h2>
<input type='submit' name='saveAuth' value='保存'>

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

if __name__ == "__main__":

	logger.debug( '---------- batch start ------------' )
	srcid = sys.argv[1]
	dstid = sys.argv[2]

	auth = gCalClient.GCalendarAuth.GCalendarAuth(None, True)

	try:
		auth.refresh()
		# 有効な認証かを確認？
		auth.authorize()
		service = gCalClient.GCalendar.GCalendarService(auth, prohibitionId)
	except Exception, e:
		type, value, tb = sys.exc_info()
		tblist = traceback.format_exception(type, value, tb)
		for tb in tblist:
			logger.debug(tb)

	srcCalendar = service.getCalendar( srcid )
	dstCalendar = service.getCalendar( dstid )
	logger.debug( srcCalendar.getName() )
	logger.debug( dstCalendar.getName() )

	count, delcount, html = srcCalendar.syncTo( dstCalendar, timedelta(hours=12) )
	logger.debug( u'同期件数 ' + str(count) + u' 件 ')
	logger.debug( u'(内削除データ ' + str(delcount) + u' 件)')
	logger.debug( u'同期データ')
