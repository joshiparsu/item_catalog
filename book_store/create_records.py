from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base

from database_setup import Books
from database_setup import Users
from database_setup import UserReadingList
from database_setup import BookReviews

from datetime import datetime
import json

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

# load data from JSON file
with open('database_records.json', 'rb') as file:
    data = json.load(file)

# Loop through 'books' data, create 'Book' object for each iteration
# and store in database
for item in data['books']:
    book = Books(id=item['id'],
                title=item['title'],
                author=item['author'],
                publisher=item['publisher'],
                genre=item['genre'],
                description=item['description'],
                image_url=item['image_url'],
                buy_link=item['buy_link'],
                publish_date=datetime.strptime(item['publish_date'], '%Y-%m-%d'))
    session.add(book)

for item in data['users']:
    user = Users(email_id=item['email_id'],
                 id=item['id'],
                 name=item['name'],
                 image=item['image'])
    session.add(user)

for item in data['userreadinglist']:
    readingListEntry = UserReadingList(user_id=item['user_id'],
                                       book_id=item['book_id'])
    session.add(readingListEntry)

for item in data['bookreviews']:
    review = BookReviews(book_id=item['book_id'],
                         user_id=item['user_id'],
                         comment=item['comment'],
                         comment_date=datetime.strptime(item['comment_date'], '%Y-%m-%d'))
    session.add(review)

# Commit imported data to database
session.commit()

# Display messgae to console to verify import in complete
print "import complete"