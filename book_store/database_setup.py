import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String, Date, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class Books(Base):
    __tablename__ = 'books'
   
    id = Column(Integer, primary_key=True)
    title = Column(String(50), nullable=False)
    author = Column(String(50), nullable=False)
    publisher = Column(String(50), nullable=False)
    genre = Column(String(25), nullable=False)
    description = Column(String(1500), nullable=False)
    image_url = Column(String(500), nullable=False)
    buy_link = Column(String(500), nullable=False)
    publish_date = Column(Date, nullable=False)
    '''
    rating = Column(Integer)
    '''

    @property
    def serialize(self):
        return {
            'id' : self.id,
            'title' : self.title,
            'author' : self.author,
            'publisher' : self.publisher,
            'genre' : self.genre,
            'description' : self.description,
            'image_url' : self.image_url,
            'buy_link' : self.buy_link,
            'publish_date' : str(self.publish_date.isoformat()),
            #'rating' : self.rating
        }

class Users(Base):
    __tablename__ = 'users'

    email_id = Column(String(50), primary_key=True)
    id = Column(Integer, nullable = False)
    name = Column(String(50), nullable = False)
    image = Column(String(500), nullable = False)


class BookReviews(Base):
    __tablename__ = 'bookreviews'
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey('books.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    comment =  Column(String(1200))
    comment_date = Column(Date, nullable=False)
    book = relationship(Books)
    user = relationship(Users)

class UserReadingList(Base):
    __tablename__ = 'userreadinglist'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    book_id = Column(Integer, ForeignKey('books.id'))
    book = relationship(Books)
    user = relationship(Users)

engine = create_engine('sqlite:///yourreads.db')
Base.metadata.create_all(engine)