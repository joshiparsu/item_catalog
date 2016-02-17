from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from flask import flash
from flask import jsonify
from flask import session as login_session
from flask import make_response

from flask.ext.seasurf import SeaSurf

from sqlalchemy import create_engine
from sqlalchemy import desc
from sqlalchemy import func
from sqlalchemy import and_

from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from database_setup import Base

from database_setup import Books
from database_setup import Users
from database_setup import BookReviews
from database_setup import UserReadingList

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

from datetime import datetime

from functools import wraps

import random
import string
import httplib2
import json
import requests
import bleach
import time
import dicttoxml


app = Flask (__name__)
csrf = SeaSurf(app)

CLIENT_ID = json.loads(open('client_secret.json', 'r').read())['web']['client_id']

engine = create_engine('sqlite:///yourreads.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

# A decorator method that makes sure that the request received is only served
# if user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if login_session['logged_in'] is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# A decorator method that makes sure that the request received is only served
# if user is logged in is indeed mataches with the request sent by user
def owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        content = json.loads(request.data)
        userid = int(content['userid'])
        if login_session['user_id'] != userid:
            response = make_response(json.dumps('Current logged-in user id does not match.'),200)
            response.headers['Content-Type'] = 'application/json'
            return response
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET'])
def HomePage():
    featured_books = session.query(Books).\
                             order_by(Books.publish_date).\
                             limit(3)

    new_books = session.query(Books).\
                        order_by(desc(Books.publish_date)).\
                        limit(3)

    return render_template('index.html',
                            featured_books=featured_books,
                            new_books=new_books)


@app.route('/logIn')
def logIn():
    # create a state token to prevent request forgery
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state

    return render_template('login.html',
                            STATE=state)

# Disconnect based on provider
# In future can be extended to let user login using other providers
# except "gplus"
@app.route('/logout')
@login_required
def logout():
    if 'provider' in login_session:
        gdisconnect()
        del login_session['gplus_id']
        del login_session['credentials']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        del login_session['logged_in']
        del login_session['state']
        return redirect(url_for('HomePage'))
    else:
        return redirect(url_for('HomePage'))

# Show particular book details request by user
# Note that if user is logged in, we would let user write review for the
# listed book as well as we will let user add and/or remove the book from
# his/her list
@app.route('/book/show/<int:book_id>')
def showBook(book_id):
    reviews = session.query(BookReviews.comment, BookReviews.comment_date,\
                            Users.name, Users.image).\
                            join(Books).\
                            join(Users).\
                            filter(and_(Books.id == BookReviews.book_id, \
                                        BookReviews.user_id == Users.id)).\
                            filter(BookReviews.book_id == book_id).\
                            all()
    query = None
    read_by_user = True
    if login_session.get('logged_in',None) is not None:
        query = session.query(func.count(UserReadingList.user_id).\
                              label('read_count')).\
                              filter(and_(UserReadingList.book_id == book_id,\
                                          UserReadingList.user_id == login_session['user_id'])).\
                              first()

    if query is None or query[0] == 0:
        read_by_user = False

    book = session.query(Books).\
                   filter_by(id = book_id).\
                   one()
    related_books = session.query(Books).\
                            filter(Books.genre == book.genre,\
                                   Books.title != book.title).\
                            limit(4)

    return render_template('details.html',
                            book=book,
                            reviews=reviews,
                            related_books=related_books,
                            read_by_user=read_by_user)

# User is going thorough various books on page-by-page basis
@app.route('/book/list/', methods=['GET'])
@app.route('/book/list/<int:page>', methods=['GET'])
def listBooks(page=1):

    # We want to limit only 8 items per page
    PER_PAGE_ITEMS = 8

    rows = session.query(func.count(Books.id)).scalar()
    if rows % PER_PAGE_ITEMS != 0:
        total_pages = (int(rows/PER_PAGE_ITEMS))+1
    else:
        total_pages = (int(rows/PER_PAGE_ITEMS))

    books = session.query(Books).\
                    all()[page * PER_PAGE_ITEMS - PER_PAGE_ITEMS : page * PER_PAGE_ITEMS]

    return render_template('list_books.html',
                            books=books,
                            active_page=page,
                            total_pages=total_pages)

# If user is looged in, he/she can see what all books are added to his/her reading list.
# While going through this list, user can remove book from his/her list too.
@app.route('/userReadingList', methods=['GET'])
@login_required
def userReadingList():
    user_books = session.query(UserReadingList.book_id,\
                               Books.title, Books.description, Books.image_url,\
                               Users.name, Users.image).\
                         join(Books).\
                         join(Users).\
                         filter(and_(UserReadingList.book_id == Books.id,\
                                     UserReadingList.user_id == login_session['user_id'])).\
                         all()

    return render_template('user_list.html',
                            user_books=user_books)

# If user is logged in, he/she can see what all reviews are posted by him/her. User can
# modify the existing review, delete a review etc.
@app.route('/userReviews', methods=['GET'])
@login_required
def userReviews():
    reviews = session.query(BookReviews.comment, BookReviews.comment_date,\
                            Users.name, Users.image, \
                            Books.title, Books.image_url, Books.description, Books.id).\
                      join(Books).\
                      join(Users).\
                      filter(and_(Books.id == BookReviews.book_id, \
                                  BookReviews.user_id == login_session['user_id'])).\
                      all()

    return render_template('user_reviews.html',
                            reviews=reviews)

# Call back routine which is called when user logs-in via gplus.
# We've to keep some of the information in our session so that it is accessible at other
# places. We also have to go through couple checks to make sure user log in is successful.
@csrf.exempt
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secret.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token

    # Keep the provider and gplus id also. This is useful when we allow signin using
    # other 3rd party websites also (like facebook, github etc.)
    login_session['provider'] = 'google'
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = createUser(login_session)

    login_session['user_id'] = user_id
    login_session['logged_in'] = True

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;'
    output += '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    return output

# User is logging out.
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        print ("credentials is none")
        return response

    access_token = login_session.get('credentials')
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        print ("Failed to disconnect with" + (result['status']))
        return response

# User has requested to add or remove particular book from his/her reading list
@app.route('/processReadList', methods=['POST'])
@login_required
@owner_required
def processReadList():
    content = json.loads(request.data)
    userid = int(content['userid'])
    bookid = int(content['bookid'])
    shouldRemove = content['remove']

#    if login_session['user_id'] != userid:
#        print ("user id does not match")
#        response = make_response(json.dumps('Current logged-in user id does not match.'),200)
#        response.headers['Content-Type'] = 'application/json'
#        return response

    if shouldRemove == "false":
        wantToRead = UserReadingList(user_id=userid, book_id=bookid)
        session.add(wantToRead)
    else:
        readByUser = session.query(UserReadingList).\
                             filter(and_(UserReadingList.book_id == bookid,\
                                         UserReadingList.user_id == userid)).\
                             one()
        session.delete(readByUser)
    session.commit()

    response = make_response(json.dumps('Successfully updated.'), 200)
    response.headers['Content-Type'] = 'application/json'
    return response

# User has provided his/her review on particular book
@app.route('/processComment', methods=['POST'])
@login_required
@owner_required
def processComment():
    content = json.loads(request.data)
    userid = int(content['userid'])
    bookid = int(content['bookid'])
    raw_comment = content['comment']
    comment = bleach.clean(raw_comment, strip=True)

 #   if login_session['user_id'] != userid:
 #       response = make_response(json.dumps('Current logged-in user id does not match.'),200)
 #       response.headers['Content-Type'] = 'application/json'
 #       return response
    
    newReview = BookReviews(book_id = bookid, 
                            user_id = userid, 
                            comment = comment, 
                            comment_date = datetime.now())
    session.add(newReview)
    session.commit()

    response = make_response(json.dumps('Successfully updated.'), 200)
    response.headers['Content-Type'] = 'application/json'
    return response

# User has requested to change his/her review for particular book
@app.route('/modifyReview', methods=['POST'])
@login_required
@owner_required
def modifyReview():
    content = json.loads(request.data)
    userid = int(content['userid'])
    bookid = int(content['bookid'])
    comment = content['comment']

#    if login_session['user_id'] != userid:
#        response = make_response(json.dumps('Current logged-in user id does not match.'), 200)
#        response.headers['Content-Type'] = 'application/json'
#        return response

    new_comment = session.query(BookReviews).\
                                filter(and_(BookReviews.book_id == bookid,\
                                            BookReviews.user_id == userid)).\
                                one()
    new_comment.comment = comment
    new_comment.comment_date = datetime.now()
    session.commit()

    response = make_response(json.dumps('Successfully updated.'), 200)
    response.headers['Content-Type'] = 'application/json'
    return response

# User has requested to delete a reviews for given book
@app.route('/deleteReview', methods=['POST'])
@login_required
@owner_required
def deleteReview():
    content = json.loads(request.data)
    userid = int(content['userid'])
    bookid = int(content['bookid'])

#    if login_session['user_id'] != userid:
#        response = make_response(json.dumps('Current logged-in user id does not match.'),200)
#        response.headers['Content-Type'] = 'application/json'
#        return response
    
    comment = session.query(BookReviews).\
                      filter(and_(BookReviews.book_id == bookid,\
                                  BookReviews.user_id == userid)).\
                      one()
    session.delete(comment)
    session.commit()

    response = make_response(json.dumps('Successfully updated.'), 200)
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route('/contactMe', methods=['GET'])
def contactMe():
    return render_template('contact.html')

@app.route('/userFeedback', methods=['POST'])
def userFeedback():
    content = json.loads(request.data)
    submitter = content['submitter']
    email_id = content['email_id']
    message = content['message']

    output = ''
    output += '<h1>Your messasge is submitted.</h1>';
    output += '<h2>Give me sometime and I\'ll get back to you.</h2>'
    output += '<h2>Thanks!!</h2>'
    return output

@app.route('/jsonifyBooks', methods=['GET'])
def jsonifyBooks():
    books = session.query(Books).\
                    order_by(Books.publish_date).\
                    all()

    return jsonify(books=[book.serialize for book in books])

@app.route('/xmlifyBooks', methods=['GET'])
def xmlifyBooks():
    books = session.query(Books).all()

    content = []
    content.append('<?xml version="1.0" encoding="UTF-8"?>')
    content.append("<Books>")
    
    for book in books:
        book.serializeToXml(content)

    content.append("</Books>")
    responseContent = str.join("\n", content)
    responseContent = responseContent.replace('&', '&amp;')
    response = make_response(responseContent, 200)
    response.headers['Content-Type'] = 'text/xml'
    return response

# User Helper Functions
# Creates a new user if already not created
def createUser(login_session):
    try:
        user = session.query(Users).\
                       filter_by(email_id=login_session['email']).\
                       one()
    except NoResultFound:
        user = None

    if user is None:
        newUserId = session.query(func.count(Users.id)).\
                                  scalar()
        newUser = Users(name=login_session['username'], id=newUserId+1, image=login_session['picture'], email_id=login_session['email'])
        session.add(newUser)
        session.commit()
    user = session.query(Users).\
                   filter_by(email_id=login_session['email']).\
                   one()
    return user.id

if __name__ == '__main__':
    app.secret_key = 'Super_Secret_Key'
    app.debug = True
    app.run(host = '0.0.0.0', port = 8080)