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


class UserHandler(webapp.RequestHandler):
    
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

      # identify the user profile being displayed
      userKey = self.request.get("user")
      if len(userKey) == 0:
          logging.debug("seeking profile page without a key...")
          userQuery = db.GqlQuery("SELECT __key__ FROM UserPrefs WHERE email = :1", activeUser.email())
          userKey = userQuery.get()
          if userKey is None:
              createUser(activeUser)
              userKey = userQuery.get()
              self.redirect('/user/edit?user='+str(userKey)+'&init=yes')
              return
              
      logging.info("user key is %s" % userKey)
      user = db.get(userKey)
      if user is None:
          logging.info("Can't find this user!?! userKey sent from the client is %s" % userKey)
          # this should never be the case so bail back to the front page if it does
          self.redirect("/")
          return

      # get a list of books this user has CHECKED OUT
      logging.info("query books this user has checked out %s" % user.userID)
      borrowQuery = db.GqlQuery("SELECT * FROM Book WHERE borrower = :1", user)
      borrowed = borrowQuery.fetch(20)
      results = []
      for b in borrowed:
          logging.info("borrowed book: %s" % b.title)
          results.append({'title':'<a class="book" href=javascript:redirectBook("'+str(b.key())+'")>'+b.title+'</a>',
                        'author':b.author,
                        'status':'<a class=checkin href=javascript:checkin("'+str(b.key())+'")>checkin</a>',
                       })      

      # get a list of this user's OWNED BOOKS
      logging.info("query books with user ID %s" % user.userID)
      bookQuery = db.GqlQuery("SELECT * FROM Book WHERE userID = :1", user.userID)
      # @fixme control the query limit better
      books = bookQuery.fetch(20)
      for b in books:
        logging.info("book: %s" %b.title)
        results.append({'title':'<a class="book" href=javascript:redirectBook("'+str(b.key())+'")>'+b.title+'</a>',
                        'author':b.author,
                        'status':' ',
                       })

      # get a list of COMMENTS on this user's profile
      q = db.GqlQuery("SELECT * FROM Comment WHERE userID = :1 ORDER BY dateAdded DESC", user.userID)
      comments = q.fetch(10)
      userComments = []
      for c in comments:
        logging.info("comment: %s" % c.text)
        userComments.append({'text':c.text,
                             'author':'<a class="user" href=javascript:redirectUser("'+str(c.commentAuthor.key())+'")>'+c.commentAuthor.nickname+'</a>',
                             }
                            )
      if user.userID == activeUser.user_id():
          edit = '<div id="edit"><a href=/user/edit?user='+str(userKey)+'>edit</a></div>'
      else:
          edit = ' '

      # add the counter to the template values
      template_values = {'nickname':user.nickname,
                         'userEmail':user.email,
                         'userIDKey':str(user.key()),
                         'greeting':greeting,
                         'books':results,
                         'comments':userComments,
                         'edit':edit,
                        }
      
      # generate the html
      path = os.path.join(os.path.dirname(__file__), 'user.html')
      self.response.out.write(template.render(path, template_values))


##  end UserHandler

class UserEditHandler(webapp.RequestHandler):
    
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
        
        # grab the user's current profile data to populate the form
        user = db.get(self.request.get("user"))
        if user is None:
            logging.error("User edit attempt with no logged in user. This should never happen, %s" % self.request.get("user"))
            return
        
        if self.request.get('init') == 'yes':
            welcome = "<div id=welcome>Welcome to Frinook! Please take a moment to fill out your profile. Thanks!</div>"
        else:
            welcome = ' '
            
        logging.info("User: %s", user.nickname)
        first = ' ' if user.first is None else user.first
        last = ' ' if user.last is None else user.last
        nickname = first + ' ' + last if user.nickname is None else user.nickname
        email = user.email if user.preferredEmail is None else user.preferredEmail
        
        template_values = {'nickname':nickname,
                           'preferredEmail':email,
                           'greeting':greeting,
                           'first':first,
                           'last':last,
                           'userKey':self.request.get('user'),
                           'welcome':welcome,
                          }
        path = os.path.join(os.path.dirname(__file__), 'profile.html')
        self.response.out.write(template.render(path, template_values))
        
## end UserEditHandler

class ProfileAjaxUpdateHandler(webapp.RequestHandler):

    def post(self):
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

        first = self.request.get('first')
        last = self.request.get('last')
        nickname = self.request.get('nickname')
        email = self.request.get('email')
        userKey = self.request.get('userKey')
        
        user = db.get(userKey)
        if user is None:
            logging.error("Profile update attempt with no logged in user. This should never happen, %s" % userKey)
            return
        
        logging.info("Updating profile for %s with %s, %s, %s, %s" % (userKey,first,last,nickname,email))
        user.first = first
        user.last = last
        user.nickname = nickname
        user.preferredEmail = email
        user.put()
        
        self.redirect('/user')
        #self.response.out.write('yes')

## end ProfileAjaxUpdateHandler

class AddCommentHandler(webapp.RequestHandler):
    
    def post(self):
      activeUser = users.get_current_user()
      logging.info("new comment: %s" % self.request.get("comment"))

      userKey = self.request.get("pageOwner")
      user = db.get(userKey)
      if activeUser:
        comment = Comment()
        comment.text = self.request.get("comment")
        comment.commentAuthor = getUser(activeUser.user_id())
        comment.pageOwner = user
        comment.userID = user.userID
        comment.put()        
      else:
        logging.error("Illegal comment request!?! Comment is... %s" % self.request.get("comment"))
      
      logging.info('comment added... now return nickname %s' % activeUser.nickname())  
      self.response.out.write(activeUser.nickname())
        
## end AddCommentHandler

def getUser(userID):
    userQuery = db.GqlQuery("SELECT * FROM UserPrefs WHERE userID = :1", userID)
    users = userQuery.fetch(1)
    if len(users) == 0:
        logging.info("We can't find this user in the UserPrefs table... userID: %s" % userID)
        return None
    else:
        return users[0]
    
## end getUser()

def createUser(activeUser):
    
        newUser = UserPrefs()
        newUser.user = activeUser
        newUser.userID = activeUser.user_id()
        newUser.email = activeUser.email()
        newUser.nickname = activeUser.nickname()
        newUser.status = ""
        logging.info("Creating profile for %s" % newUser.email)
        newUser.put()
        return

## end createUser()          

def main():
  application = webapp.WSGIApplication([('/user', UserHandler),
                                        ('/user/edit', UserEditHandler),
                                        ('/user/addcomment', AddCommentHandler),
                                        ('/user/update', ProfileAjaxUpdateHandler),
                                        ],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
