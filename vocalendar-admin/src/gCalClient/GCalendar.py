# coding=utf-8
'''
Created on 2012/03/06

@author: mryou

'''
import os
import logging
from datetime import datetime, timedelta
from apiclient.discovery import build
from apiclient.errors import HttpError

logger = logging.getLogger(__name__)

class GCalendarService():
    '''
        Googleカレンダーサービスを扱うクラス
    '''

    def __init__( self, GCalendarAuth, prohibitionId='' ):
        '''
            @param GCalendarAuth: 認証情報
            @param prohibitionId: 編集不可とするカレンダーID
        '''

        self._auth = GCalendarAuth
        self.service = build(serviceName='calendar', version='v3', http=self._auth.http, developerKey=self._auth.developerKey)
        self.prohibitionId = prohibitionId

    def getCalendars(self):
        '''
            利用可能なカレンダー一覧を取得
        '''

        calendars = self.service.calendarList().list().execute()

        # 編集不可のカレンダーに対して、editble=falseのフラグを付与
        if 'items' in calendars:
            for calendar in calendars.get('items'):
                calendar['editable'] = ( calendar.get('id') != self.prohibitionId )
            return calendars['items']
        return []

    def getCalendar(self, calId):
        '''
            指定されたIDのカレンダー（GCalendar)のインスタンスを取得
        '''

        logger.debug(u'getCalendar')
        logger.debug(calId)
        gcalendar = GCalendar( self.service, self.service.calendars().get(calendarId=calId).execute())
        gcalendar.calendar['editable'] = ( gcalendar.getId() != self.prohibitionId )
        return gcalendar


class GCalendar():
    '''
        Googleカレンダーを扱うクラス
    '''

    def __init__(self, service, calendar):
        self.service = service
        self.calendar = calendar

    def getName(self):
        '''
            カレンダー名称の取得
        '''
        return self.calendar['summary']

    def getId(self):
        '''
            カレンダーIDの取得
        '''
        return self.calendar['id']

    # idがあるとダメなので同期には使えない
    def create(self, event):
        '''
            予定の登録処理
            @param event: 予定データ（json)
            @return: 作成された予定データ
        '''


        logger.debug('create')
        logger.debug(event.get('id'))

        # 既存データをそのまま渡されてきたような場合に備えて不要な属性を削除する。
        # idはもちろん、iCalUIDがあるとそこからIDを生成するので削除
        event.pop('id', None)
        event.pop('iCalUID', None)
        event.pop('organizer', None)
        event.pop('status', None)
        # なぜかタイムゾーン情報がないとエラーになる
        event['start']['timeZone']='Asia/Tokyo'
        event['end']['timeZone']='Asia/Tokyo'

        try:
            created = self.service.events().insert(calendarId=self.getId(), body=event).execute()
            # わざわざpassを入れているのはdebugで↑をコメントアウトしたときにエラーにならないように(^_^;)
            pass
        except HttpError, e:
            print e
            raise
        return created

    def getEvent(self, eventid):
        '''
            予定の取得処理
            @param eventid: id属性
            @return: 予定データ
        '''
        try:
            event = self.service.events().get(calendarId=self.getId(), eventId=eventid).execute()
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
        '''
            繰り返し予定の取得処理
            @param eventid: id属性
            @return: 繰り返し予定データ
        '''
        try:
            events = self.service.events().instances(calendarId=self.getId(), eventId=eventid).execute()
            pass
        except HttpError, e:
            # not found（対象無し）は無視
            if e.resp.status == 404:
                return None
            else:
                raise
        return events

    def update(self, event):
        '''
            予定の更新処理
            @param event: 予定データ（json)
        '''
        try:
            self.service.events().update(calendarId=self.getId(), eventId=event.get('id'), body=event).execute()
            pass
        except HttpError, e:
            print e
            raise

    def delete(self, eventid):
        '''
            予定の削除処理
            @param eventid: id属性
        '''

        try:
            self.service.events().delete(calendarId=self.getId(), eventId=eventid).execute()
            pass
        except HttpError, e:
            # not found（対象無し） or Resource has been deleted（削除済み）は無視
            if not ( e.resp.status == 404 or e.resp.status == 410 ):
                raise


    # import_なのはimportが予約後だから。
    def import_(self, event):
        '''
            他のカレンダーからの予定のインポート処理。
            @param event: 予定データ（json)
        '''

        target = dict(event)
        # 同期のキーはiCalUIDなのでidは不要。むしろ邪魔
        target.pop('id', None)
        target.pop('organizer', None)
        target['start']['timeZone']='Asia/Tokyo'
        target['end']['timeZone']='Asia/Tokyo'

        try:
            self.service.events().import_(calendarId=self.getId(), body=target).execute()
            return u'インポート:'
        except HttpError, e:
            print event
            print e
            raise


    def getEvents(self, **arg):
        '''
            予定一覧の取得（更新順）
            @param arg: 追加検索条件
        '''
        param = {
                'calendarId': self.calendar['id'],
                'timeMin': '1970-01-01T00:00:00Z',
                #'timeMax': '2039-12-31T00:00:00Z',
                'orderBy': 'updated'
                }
        param.update(arg)
        events = self.service.events().list(**param).execute()
        return events

    # --------------
    # ここから下のメソッド群はGCalendarクラスにあるのは不自然な気がしてる。
    # --------------

    def getCount(self, description=False, onlyDelData=False):
        '''
            件数一覧の取得。
            予定データ、件数のファイル保存も実施
            @param description: 予定データファイルに詳細情報を含めるかどうか
            @param onlyDelData: 削除データのみ対象とする
        '''

        logger.debug(u'件数カウント'.encode('utf-8'))
        logger.debug(description)
        logger.debug(onlyDelData)

        count = 0
        html = u''
        param = {
                'showDeleted': onlyDelData
                }

        # 1ページ目取得
        events = self.getEvents(**param)

        # index.wsgiのあるディレクトリのファイルを保存したいので。
        filedir = os.path.dirname(__file__)
        while not os.path.exists( os.path.join( filedir, 'index.wsgi' ) ):
            filedir = os.path.split( filedir )[0]

        # 件数カウントとファイル作成の処理を分けた方が良いと思うんだよね。
        datafilename = self.getId() + u'.csv'
        datafile = open( os.path.join( filedir , datafilename), 'w' )
        datafile.writelines(u'ステータス\t開始日\t終了日\tID\t件名\t作成者\t作成日\t更新時間\t更新回数\t詳細\n')

        while events.has_key('items'):
            count += len( events.get('items') )
            # 予定データを1件ずつ処理
            for event in events.get('items'):

                # 削除のみの場合は削除データ以外スルー
                if onlyDelData:
                    if not event.get('status') == 'cancelled':
                        continue

                datafile.writelines( self.toCsvString(event, description).encode('utf-8') )
                datafile.writelines( u'\n' )

            # 次ページがあれば取得する
            page_token = events.get('nextPageToken')
            if page_token:
                param['pageToken'] = page_token
                events = self.getEvents(**param)
            else:
                break

        html += u'</br>'
        html += u"<a href='./" + datafilename + "' target='_brank'>データダウンロード</a>"
        datafile.close()

        countfile = open( os.path.join( filedir , self.getId() + '.txt'), 'w' )
        countfile.writelines(str(count))
        countfile.close()

        return count, events['updated'], html

    def deleteAll(self):
        '''
            全件削除
            Googleの削除データの仕様がアレなので使わない方がいい
        '''

        if not self.calendar.get('editable'):
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

    def syncTo(self, dstCalendar, syncAllData=False):
        '''
            予定情報の同期。
            同期先は自分自身。同期元となったカレンダーの最終更新日より1日前のデータ以降を同期する。
            @param dstCalendar: 同期先カレンダーインスタンス（GCalendar)
            @param syncAllData: 1日前からの差分ではなく全件とする
        '''

        count = 0
        delcount = 0
        html = u''
        param = {
                'showDeleted': True
                }

        # 同期先の最終更新日から1日前の日付文字列を生成
        if not syncAllData:
            dstEvents = dstCalendar.getEvents()
            lastModifiedStr = dstEvents.get('updated').split( '.' )[0].split('Z')[0]
            lastModified = datetime.strptime(lastModifiedStr, '%Y-%m-%dT%H:%M:%S')
            minUpdate = lastModified - timedelta(days=1)
            minUpdateStr = minUpdate.strftime('%Y-%m-%dT%H:%M:%SZ')
            param['updatedMin'] = minUpdateStr

        events = self.getEvents(**param)
#        file = open( os.path.join(os.path.dirname(__file__) , 'alldata.csv'), 'w' )
        while events.has_key('items'):
            for event in events.get('items'):
                count += 1
#                file.write( ( self.toCsvString(event) + u'\n').encode('utf-8') )

                if event.get('status') == 'cancelled':
                    delcount += 1
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

#        html += u'</br>'
#        html = u"<a href='./alldata.csv' target='_brank'>データダウンロード</a>"
#        file.close()

        return count, delcount, html

    # 大量削除の対応用。
    def cancelDelete(self):

        logger.debug(u'cancelDelete')

        count = 0
        delcount = 0
        html = u''
        param = {
                'showDeleted': True,
                'updatedMin' : '2012-03-30T00:00:00.000Z'
                }

        events = self.getEvents(**param)
        while events.has_key('items'):
            for event in events.get('items'):
                count += 1

                if event.get('status') == 'cancelled':
                    delcount += 1
                    # createじゃなくてimportにするべきだった・・・orz（createrが自分になっちゃた）
                    created = self.create(event)
                    html += u'削除取消:' + self.toString(created)
                    html += u'</br>'
                    continue

            page_token = events.get('nextPageToken')
            if page_token:
                param['pageToken'] = page_token
                events = self.getEvents(**param)
            else:
                break

        return count, delcount, html

    def getEventColor(self ):
        '''
            イベントに設定できる色一覧の取得
        '''
        result = self.service.colors().get().execute()
        return result.get('event')

    def changeEventColor( self, colSearchStr, colorid ):
        '''
            指定された文字列がsummaryにあるイベントに指定色を設定
            @param colSearchStr: 検索文字列
            @param colorid: カラーID
        '''

        count = 0
        html = u''
        param = {}

        events = self.getEvents(**param)

        while events.has_key('items'):
            for event in events.get('items'):

                logger.debug(event.get('id'))
                logger.debug(event.get('summary'))

                if event.get('summary') is None:
                    continue

                if colSearchStr in event.get('summary'):
                    count += 1
                    event['colorId'] = colorid
                    self.update(event)
                    html += u'変更:' + self.toString(event)
                    html += u'</br>'
                    continue

            page_token = events.get('nextPageToken')
            if page_token:
                param['pageToken'] = page_token
                events = self.getEvents(**param)
            else:
                break

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

    def toCsvString(self, event, description=False):
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
        csv += event.get('status')
        csv += u'\t'
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

        if description:
            desctemp = event.get('description')
            if desctemp is not None:
                desctemp = desctemp.replace('\n', ' ')
                desctemp = desctemp.replace('\t', ' ')
                csv += u'\t'
                csv += desctemp

        return csv

class GCalEvent():
    '''
        Googleカレンダーのイベントを扱うクラス
        まだ未使用。
    '''

    def __init__( self, event ):
        self.event = event

    def toString(self):

        if self.event.get('start') is None:
            return u'詳細不明 id: ' + self.event.get('id')

        eventdate = self.event.get('start').get('date')
        if not self.event.get('start').has_key('date'):
            eventdate = self.event.get('start').get('dateTime')
        summary = self.event.get('summary')
        if summary is None:
            summary = u'(ブランク)'
        return self.event.get('status') + u':' + self.event.get('updated') + u':'+ eventdate + u':' + summary

    def toCsvString(self):
        if self.event.get('start') is None:
            return u'詳細なし id: ' + self.event.get('id')

        startdate = self.event.get('start').get('date')
        if not self.event.get('start').has_key('date'):
            startdate = self.event.get('start').get('dateTime')

        enddate = self.event.get('end').get('date')
        if not self.event.get('end').has_key('date'):
            enddate = self.event.get('end').get('dateTime')

        summary = self.event.get('summary')
        if summary is None:
            summary = u'(ブランク)'

        csv = u''
        csv += startdate
        csv += u'\t'
        csv += enddate
        csv += u'\t'
        csv += self.event.get('id')
        csv += u'\t'
        csv += summary
        csv += u'\t'
        csv += self.event.get('creator').get('email')
        csv += u'\t'
        csv += self.event.get('created')
        csv += u'\t'
        csv += self.event.get('updated')
        csv += u'\t'
        csv += str(self.event.get('sequence'))

        return csv

