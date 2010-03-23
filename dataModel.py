from google.appengine.ext import db

class ApprovedUsers(db.Model):
    email = db.StringProperty()
    
# a user wrapper that...
#  1. maintains a list of userIDs
#  2. provides an opportunity to configure user info
#     within frinook but not google
#
class UserPrefs(db.Model):
    user              = db.UserProperty()
    userID            = db.StringProperty()
    email             = db.StringProperty()
    preferredEmail    = db.StringProperty()
    nickname          = db.StringProperty()
    status            = db.StringProperty()
    first             = db.StringProperty()
    last              = db.StringProperty()
    birthdate         = db.DateProperty()
    
class Book(db.Model):
    title            = db.StringProperty()
    author           = db.StringProperty()
    thumbnailURL     = db.StringProperty()
    subject          = db.StringProperty()
    summary          = db.StringProperty(multiline=True)
    isbn             = db.StringProperty()
    googleVolumeURL  = db.StringProperty()
    
    userID           = db.StringProperty()
    owner            = db.ReferenceProperty(UserPrefs,collection_name="book_owner_set")
    borrower         = db.ReferenceProperty(UserPrefs,collection_name="book_borrower_set")
    dateAdded        = db.DateTimeProperty(auto_now_add=True)
    dateLastModified = db.DateTimeProperty(auto_now=True)
    checkedOut       = db.BooleanProperty()

class Comment(db.Model):
    text          = db.StringProperty(multiline=True)
    userID        = db.StringProperty()
    commentAuthor = db.ReferenceProperty(UserPrefs,collection_name="comment_commentauthor_set")
    pageOwner     = db.ReferenceProperty(UserPrefs,collection_name="comment_pageowner_set")
    dateAdded     = db.DateTimeProperty(auto_now_add=True)
    
class BookReview(db.Model):
    book         = db.ReferenceProperty(Book)
    text         = db.StringProperty(multiline=True)
    reviewerID   = db.StringProperty()
    reviewer     = db.ReferenceProperty(UserPrefs)
    dateReviewed = db.DateTimeProperty(auto_now_add=True)

class UserEvent(db.Model):
    user      = db.ReferenceProperty(UserPrefs,collection_name="event_user_set")
    eventType = db.StringProperty()
    dateAdded = db.DateTimeProperty(auto_now_add=True)
    comment   = db.ReferenceProperty(Comment,collection_name="event_comment_set")
    book      = db.ReferenceProperty(Book,collection_name="event_book_set")
    review    = db.ReferenceProperty(BookReview,collection_name="event_review_set")
    