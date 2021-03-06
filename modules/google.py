import gflags
import httplib2
from datetime import timedelta, date
import dateutil.parser
from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run
import json, os, inspect
from pymongo import MongoClient
from lisa import configuration

import gettext

path = os.path.realpath(os.path.abspath(os.path.join(os.path.split(
    inspect.getfile(inspect.currentframe()))[0],os.path.normpath("../lang/"))))
_ = translation = gettext.translation(domain='google', localedir=path, languages=[configuration['lang']]).ugettext

class Google:
    def __init__(self, lisa=None):
        self.configuration_lisa = configuration
        mongo = MongoClient(self.configuration_lisa['database']['server'],
                            self.configuration_lisa['database']['port'])
        self.configuration = mongo.lisa.plugins.find_one({"name": "Google"})

    def getCalendars(self,args):
        FLAGS = gflags.FLAGS

        # Set up a Flow object to be used if we need to authenticate. This
        # sample uses OAuth 2.0, and we set up the OAuth2WebServerFlow with
        # the information it needs to authenticate. Note that it is called
        # the Web Server Flow, but it can also handle the flow for native
        # applications
        # The client_id and client_secret are copied from the API Access tab on
        # the Google APIs Console
        FLOW = OAuth2WebServerFlow(
            client_id=self.configuration['configuration']['account']['client_id'],
            client_secret=self.configuration['configuration']['account']['client_secret'],
            scope='https://www.googleapis.com/auth/calendar',
            user_agent='LISA/0.1')

        # To disable the local server feature, uncomment the following line:
        FLAGS.auth_local_webserver = False

        # If the Credentials don't exist or are invalid, run through the native client
        # flow. The Storage object will ensure that if successful the good
        # Credentials will get written back to a file.
        storage = Storage('tmp/calendar.dat')
        credentials = storage.get()
        if credentials is None or credentials.invalid == True:
            credentials = run(FLOW, storage)

        # Create an httplib2.Http object to handle our HTTP requests and authorize it
        # with our good Credentials.
        http = httplib2.Http()
        http = credentials.authorize(http)

        # Build a service object for interacting with the API. Visit
        # the Google APIs Console
        # to get a developerKey for your own application.
        service = build(serviceName='calendar', version='v3', http=http,
                        developerKey=self.configuration['configuration']['account']['developer_key'])

        event_list = {}
        today = date.today()
        tomorrow = today + timedelta(days=1)
        for calendar in self.configuration['configuration']['account']['calendars']:
            page_token = None
            while True:
                events = service.events().list(calendarId=calendar['id'],pageToken=page_token).execute()
                if events['items']:
                    for event in events['items']:
                        if event['start']['dateTime']:
                            event_date = dateutil.parser.parse(event['start']['dateTime']).date()
                            event_time = dateutil.parser.parse(event['start']['dateTime']).time()
                            if (args[0] == _('today')) and (today == event_date):
                                event_list[event_time] = event['summary']
                            if (args[0] == _('tomorrow')) and (tomorrow == event_date):
                                event_list[event_time] = event['summary']
                page_token = events.get('nextPageToken')
                if not page_token:
                    break
        if not event_list.items():
            return _('no_event')
        sorted = event_list.items()
        sorted.sort()
        list_event_str = _('events_scheduled') % args[0]
        first = True
        for event_time, event_summary in sorted:
            if first == False:
                list_event_str = list_event_str + _(' then ')
            list_event_str = list_event_str + event_summary+ _(' at ') + event_time.strftime(_('time'))
            first = False
        return json.dumps({"plugin": "google","method": "getCalendars",
                           "body": list_event_str})