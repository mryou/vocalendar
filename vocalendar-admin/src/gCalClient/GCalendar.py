# coding=utf-8
'''
Created on 2012/03/06

@author: mryou

'''
import os
import logging
logger = logging.getLogger(__name__)
from datetime import datetime, timedelta
from apiclient.discovery import build
from apiclient.errors import HttpError

class GCalendarService():

    def __init__( self, GCalendarAuth, prohibitionId='' ):

        self._auth = GCalendarAuth
        self.service = build(serviceName='calendar', version='v3', http=self._auth.http, developerKey=self._auth.developerKey)
        self.prohibitionId = prohibitionId

    def getCalendars(self):
        calendars = self.service.calendarList().list().execute()
        if 'items' in calendars:
            for calendar in calendars.get('items'):
                calendar['editable'] = ( calendar.get('id') != self.prohibitionId )
            return calendars['items']
        return []

    def getCalendar(self, calId):
        logger.debug(calId)
        gcalendar = GCalendar( self.service, self.service.calendars().get(calendarId=calId).execute())
        gcalendar.calendar['editable'] = ( gcalendar.getId() != self.prohibitionId )
        return gcalendar


class GCalendar():

    def __init__(self, service, calendar):
        self.service = service
        self.calendar = calendar

    def getName(self):
        return self.calendar['summary']

    def getId(self):
        return self.calendar['id']

    # idがあるとダメなので同期には使えない
    def create(self, event):
        event.pop('id', None)
        event.pop('organizer', None)
        event['start']['timeZone']='Asia/Tokyo'
        event['end']['timeZone']='Asia/Tokyo'

        try:
            self.service.events().insert(calendarId=self.getId(), body=event).execute()
            pass
        except HttpError, e:
            print e
            raise

    def getEvent(self, eventid):
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
        try:
            self.service.events().update(calendarId=self.getId(), eventId=event.get('id'), body=event).execute()
            pass
        except HttpError, e:
            print e
            raise

    def delete(self, eventid):

        try:
            self.service.events().delete(calendarId=self.getId(), eventId=eventid).execute()
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
            self.service.events().import_(calendarId=self.getId(), body=target).execute()
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

    def getCount(self, description=False, onlyDelData=False):
        logger.debug(u'件数カウント'.encode('utf-8'))
        logger.debug(description)
        logger.debug(onlyDelData)

        count = 0
        html = u''
        param = {
                'showDeleted': onlyDelData
                }

        events = self.getEvents(**param)

        filedir = os.path.dirname(__file__)
        while not os.path.exists( os.path.join( filedir, 'index.wsgi' ) ):
            filedir = os.path.split( filedir )[0]

        datafilename = self.getId() + u'.csv'
        datafile = open( os.path.join( filedir , datafilename), 'w' )
        datafile.writelines(u'ステータス\t開始日\t終了日\tID\t件名\t作成者\t作成日\t更新時間\t更新回数\t詳細\n')
        while events.has_key('items'):
            count += len( events.get('items') )
            for event in events.get('items'):

                if onlyDelData:
                    if not event.get('status') == 'cancelled':
                        continue

                datafile.writelines( self.toCsvString(event, description).encode('utf-8') )
                datafile.writelines( u'\n' )

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

        count = 0
        delcount = 0
        html = u''
        param = {
                'showDeleted': True
                }
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

    def getEventColor(self ):
        result = self.service.colors().get().execute()
        return result.get('event')

    def changeEventColor( self, colSearchStr, colorid ):

        count = 0
        html = u''
        param = {}

        events = self.getEvents(**param)

        while events.has_key('items'):
            for event in events.get('items'):

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

