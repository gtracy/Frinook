#!/usr/bin/env python
#
import os
import logging

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import util

from google.appengine.api.labs import taskqueue
from google.appengine.api.labs.taskqueue import Task
from dataModel import *

from google.appengine.runtime import apiproxy_errors


EVENT_BOOK_ADD = 0
EVENT_BOOK_CHECKOUT = 1
EVENT_BOOK_RETURN = 2
EVENT_BOOK_REVIEWED = 3
EVENT_BOOK_RATED = 4
EVENT_USER_NOTE = 5

   

def createEvent(eventType, 
                user,
                book,
                metaNote):

    logging.debug("EVENT: logging user event")
    event = UserEvent()
    event.eventType = eventType
    event.user = user
    event.book = book
    event.meta = metaNote
    event.put()
    
## end createEvent()    

