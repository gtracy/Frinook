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

from dataModel import *

    
class MainHandler(webapp.RequestHandler):

  def get(self):      
      buttons = """
                <div class='action-button intro-signup'>sign in</div>
                <div class='action-button intro-invite right-invite'>request an invite</div>
                """
      user = users.get_current_user()
      if user:
          q = db.GqlQuery("SELECT * FROM ApprovedUsers WHERE email = :1", user.email())
          entry = q.fetch(1)
          if len(entry) > 0:
            self.redirect("/library.html")
            return
          else:
            greeting = ("%s (<a href=\"%s\">sign out</a>)" %
                        (user.nickname(), users.create_logout_url("/")))
            buttons = "<div class='action-button intro-invite'>request an invite</div>"

      else:
          greeting = ("<a href=\"%s\">Sign in or register</a>." %
                        users.create_login_url("/"))
              
      # add the counter to the template values
      template_values = {'greeting':greeting,
                         'buttons':buttons,
                         'signinURL':users.create_login_url("/library.html"),
                        }
      
      # generate the html
      path = os.path.join(os.path.dirname(__file__), 'index.html')
      self.response.out.write(template.render(path, template_values))

## end MainHandler()


class LibraryHandler(webapp.RequestHandler):

  def get(self):
      currentUser = users.get_current_user()
      if currentUser:
          q = db.GqlQuery("SELECT * FROM ApprovedUsers WHERE email = :1", currentUser.email())
          entry = q.fetch(1)
          if len(entry) > 0:
            greeting = ("%s! (<a href=\"%s\">sign out</a>)" %
                        (currentUser.nickname(), users.create_logout_url("/")))
          else:
            self.redirect("/")
            return;
      else:
          self.redirect("/")
          return;
    
      # make sure we already have this user registered so we
      # can keep track of the ID
      userID = currentUser.user_id()
      userQ = db.GqlQuery("SELECT * FROM UserPrefs WHERE userID = :1", userID)
      u = userQ.fetch(1)
      if len(u) == 0:
          # re-direct to account creation page
          self.redirect("/user")

      results = []
      myResults = []
      
      # get a list of ALL existing books
      bookQuery = db.GqlQuery("SELECT * FROM Book WHERE userID != :1", userID)
      books = bookQuery.fetch(100)
      for b in books:
        results.append({'title':'<a class="book" href=javascript:redirectBook("'+str(b.key())+'")>'+b.title+'</a>',
                        'author':b.author,
                        'owner':'<a class="user" href=javascript:redirectUser("'+str(b.owner.key())+'")>'+b.owner.nickname+'</a>',
                        'status':'<a>out</a>' if b.checkedOut==True else '<a class=checkout href=javascript:checkout("'+str(b.key())+'")>checkout</a>',
                        }
                       )

      # get a list of books for current user
      bookQuery = db.GqlQuery("SELECT * FROM Book WHERE userID = :1 ORDER BY dateAdded DESC LIMIT 50", userID)
      books = bookQuery.fetch(100)
      for b in books:
        myResults.append({'title':'<a class="book" href=javascript:redirectBook("'+str(b.key())+'")>'+b.title+'</a>',
                          'author':b.author,
                          'borrower':' ' if b.borrower is None else '<span class="short">checked out by '+b.borrower.user.nickname()+'</span>',
                          'status':'<a class=checkin href=javascript:checkin("'+str(b.key())+'")>checkin</a>' if b.checkedOut==True else ' ',
                          }
                         )
              
      # add the counter to the template values
      template_values = {'greeting':greeting,
                         'signinURL':users.create_login_url("/library.html"),
                         'books':results,
                         'myBooks':myResults, 
                        }
      
      # generate the html
      path = os.path.join(os.path.dirname(__file__), 'library.html')
      self.response.out.write(template.render(path, template_values))
    
##  end LibraryHandler

def getUser(userID):
    userQuery = db.GqlQuery("SELECT * FROM UserPrefs WHERE userID = :1", userID)
    users = userQuery.fetch(1)
    if len(users) == 0:
        logging.info("We can't find this user in the UserPrefs table... userID: %s" % userID)
        return None
    else:
        return users[0]
    
## end getUser()

          
    
class EmailWorker(webapp.RequestHandler):
    def post(self):        
        try:
            ownerEmail = self.request.get('ownerEmail')
            borrowerEmail = self.request.get('borrowerEmail')
            body = self.request.get('body')
            logging.debug("email task running for %s", ownerEmail)
        
            # send email 
            message = mail.EmailMessage()
            message.subject = "Frinook book notification"
            message.sender='greg.tracy@att.net'                                      
            message.reply_to = borrowerEmail
            message.to = ownerEmail
            message.cc = borrowerEmail
            message.html = body
            message.send()

        except apiproxy_errors.DeadlineExceededError:
            logging.info("DeadlineExceededError exception!?! Try to set status and return normally")
            self.response.clear()
            self.response.set_status(200)
            self.response.out.write("Task took to long for %s - BAIL!" % email)

## end EmailWorker

class SendEmailHandler(webapp.RequestHandler):
    def get(self):
        sendEmail("greg.tracy@att.net,emma@emmatracy.com",
                  "Testing the email notification system in Frinook!")
        
## end SendEmailHandler

def sendEmail(email, body):
    # send email to the new user
    task = Task(url='/emailqueue', params={'email':email,'body':body})
    task.add('emailqueue')

## end sendEmail()

def main():
  application = webapp.WSGIApplication([('/', MainHandler),
                                        ('/library.html', LibraryHandler),
                                        ('/emailqueue', EmailWorker),
                                       ],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
