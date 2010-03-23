#!/usr/bin/env python
#


import os
import logging

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.db import Key
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util

from google.appengine.api import users
from google.appengine.api import mail
from google.appengine.api.labs import taskqueue
from google.appengine.api.labs.taskqueue import Task

from google.appengine.runtime import apiproxy_errors

import feedparser

from dataModel import *

class BookHandler(webapp.RequestHandler):
    
    def get(self):
      activeUser = users.get_current_user()
      logging.info("active user ID: %s" % activeUser.user_id())
      if activeUser:
          q = db.GqlQuery("SELECT * FROM ApprovedUsers WHERE email = :1", activeUser.email())
          entry = q.fetch(1)
          if len(entry) > 0:
            greeting = ("%s (<a href=\"%s\">sign out</a>)" %
                        (activeUser.nickname(), users.create_logout_url("/")))
          else:
            self.redirect("/")
            return
      else:
          self.redirect("/")
          return

      # identify the book profile being displayed
      bookKey = self.request.get("book")
      book = db.get(bookKey)
      if book is None:
          logging.info("Can't find this book!?! bookKey sent from the client is %s" % bookKey)
          # this should never be the case so bail back to the front page if it does
          self.redirect("/")
          return
      
      # get a list of this book's reviews
      bookQuery = db.GqlQuery("SELECT * FROM BookReview WHERE book = :1 ORDER BY dateReviewed DESC", book)
      reviews = bookQuery.fetch(10)
      results = []
      for c in reviews:
        results.append({'text':c.text,
                        'reviewer':'<a class="user" href=javascript:redirectUser("'+str(c.reviewer.key())+'")>'+c.reviewer.nickname+'</a>',
                        }
                       )

      # add the counter to the template values
      template_values = {'greeting':greeting,
                         'bookKey':bookKey,
                         'title':book.title,
                         'author':book.author,
                         'reviews':results,
                        }
      
      # generate the html
      path = os.path.join(os.path.dirname(__file__), 'book.html')
      self.response.out.write(template.render(path, template_values))


##  end BookHandler


class AddBookHandler(webapp.RequestHandler):
    
    def post(self):
      user = users.get_current_user()
      logging.info("author: %s" % self.request.get("author"))
      logging.info("title: %s" % self.request.get("title"))
      book = Book()
      book.title = self.request.get("title")
      book.author = self.request.get("author")
      
      book.owner = getUser(user.user_id())
      book.userID = user.user_id()
      book.borrower = None
      book.checkedOut = False
      book.put()
        
## end AddBookHandler
        
class CheckoutBookHandler(webapp.RequestHandler):
    
    def post(self):
        bookKey = self.request.get("key")
        book = db.get(bookKey)
        logging.info("checkout call made it for book: %s" % bookKey)
        if book is None:
            logging.info("Oops. I couldn't find book with that key")
        else:
            logging.info("I found your book! %s %s" % (book.title, book.author))
        
        book.checkedOut = True
        book.borrower = getUser(users.get_current_user().user_id())
        book.put() 

        # construction the email with the transaction details
        template_values = {'owner':book.owner.nickname(), 
                           'title':book.title, 
                           'borrower':users.get_current_user().nickname(),
                           'borrowerEmail':users.get_current_user().email(),
                           }       
        path = os.path.join(os.path.dirname(__file__), 'checkout-email.html')
        body = template.render(path, template_values)
        
        # send out email notification
        email = users.get_current_user().email()+","+book.owner.email()
        task = Task(url='/emailqueue', params={'ownerEmail':book.owner.email(),
                                               'borrowerEmail':users.get_current_user().email(),
                                               'body':body})
        task.add('emailqueue')

        return;
    
## end CheckoutBookHandler

         
class CheckinBookHandler(webapp.RequestHandler):
    
    def post(self):
        bookKey = self.request.get("key")
        logging.info("checkIN call made it for book: %s" % bookKey)
        k = Key(bookKey)
        book = Book.get(k)
        if book is None:
            logging.info("Oops. I couldn't find book with that key")
        else:
            logging.info("I found your book! %s %s" % (book.title, book.author))
        
        book.checkedOut = False
        book.borrower = None
        book.put() 
        
        return;
    
## end CheckinBookHandler


class AddReviewHandler(webapp.RequestHandler):
    
    def post(self):
      activeUser = users.get_current_user()
      logging.info("new review: %s" % self.request.get("review"))

      bookKey = self.request.get("book")
      book = db.get(bookKey)
      if activeUser:
          review = BookReview()
          review.text = self.request.get("review")
          review.book = book
          review.reviewerID = activeUser.user_id()
          review.reviewer = getUser(activeUser.user_id())
          review.put()
      else:
          logging.error("Illegal review request!?! review is... %s" % self.request.get("review"))
      
      logging.info('review added... now return nickname %s' % activeUser.nickname())  
      self.response.out.write(activeUser.nickname())
        
## end AddReviewHandler

def getUser(userID):
    userQuery = db.GqlQuery("SELECT * FROM UserPrefs WHERE userID = :1", userID)
    users = userQuery.fetch(1)
    if len(users) == 0:
        logging.info("We can't find this user in the UserPrefs table... userID: %s" % userID)
        return None
    else:
        return users[0]
    
## end getUser()

GOOGLE_BOOK_BASE_URL = 'http://books.google.com/books/feeds/volumes?q=isbn:'
GOOGLE_BOOK_TAIL_URL = '&max-results=1'
#def createBook(isbn):
class GetBookHandler(webapp.RequestHandler):
    def get(self):
      isbn = self.request.get('isbn')
      bookURL = GOOGLE_BOOK_BASE_URL + isbn + GOOGLE_BOOK_TAIL_URL
      atomxml = feedparser.parse(bookURL)
      entries = atomxml['entries']
      
      book = Book()
#      book.thumbnailURL =
      book.isbn = isbn
      
      output = ''
      for entry in entries:
        logging.info("entry: %s" % entry)
        for e,v in entry.iteritems():
            logging.info("%s :: %s" % (e,v))
            if e == 'title':
              stuff = book.title = v
            elif e == 'creator':
              stuff = book.author = v
            elif e == 'subject':
              stuff = book.subject = v
            elif e == 'summary':
              stuff = book.summary = v
            elif e == 'id':
              stuff = book.googleVolumeURL = v
            elif e == 'links':
                
            else:
              stuff = 'empty'
            
            output += e + ' :: ' + str(v) + ' stuff: ' + str(stuff) + '<p>'
      
      book.put()
         
      # add the counter to the template values
      template_values = {}
      
      # generate the html
      #path = os.path.join(os.path.dirname(__file__), 'book.html')
      #self.response.out.write(template.render(path, template_values))
      self.response.out.write(output)
      
      
## end getBookCover()


def main():
  application = webapp.WSGIApplication([('/book', BookHandler),
                                        ('/book/addbook', AddBookHandler),
                                        ('/book/addreview', AddReviewHandler),
                                        ('/book/checkout', CheckoutBookHandler),
                                        ('/book/checkin', CheckinBookHandler),
                                        ('/book/get', GetBookHandler)
                                        ],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
