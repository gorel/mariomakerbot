# MarioMaker Reddit Bot
# Description:
#   When activated, search a user's history on /r/MarioMaker
#   to find all levels they have submitted
# Author: Logan Gore
# Date: 2016-02-08
#

import bs4
import os
import re
from sqlalchemy import Column, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import urllib2


NUMBER_MATCH_STRING = 'typography-(\\d)'
NUMBER_PATTERN = re.compile(NUMBER_MATCH_STRING)

SLASH_MATCH_STRING = 'typography-slash'
SLASH_PATTERN = re.compile(SLASH_MATCH_STRING)

MAKER_URL = 'https://supermariomakerbookmark.nintendo.net/profile/{maker}'
LEVEL_URL = 'https://supermariomakerbookmark.nintendo.net/courses/{level}'


Base = declarative_base()


class Comment(Base):
    __tablename__ = 'comments'
    id = Column('id', String(16), primary_key=True, index=True)


class User(Base):
    __tablename__ = 'users'
    id = Column(String(128), primary_key=True, index=True)
    nnid = Column(String(128))


class Level(object):
    def __init__(self, id, url, liked, played, tried):
        self.id = id
        self.url = url
        self.liked = liked
        self.played = played
        self.tried = tried


    def format(self):
        star = 0.0
        try:
            self.tried = "{0:.2f}".format(self.tried)
            star = "{0:.2f}".format(100 * float(self.liked) / self.played)
        except:
            pass

        return "{url}|{liked}|{played}|{tried}|{star}\n".format(
            url=self.url,
            liked=self.liked,
            played=self.played,
            tried=self.tried,
            star=star,
        )


    @classmethod
    def get_number(cls, div):
        """Parse a number from a CSS class on a div"""
        try:
            for css_class in div['class']:
                match = NUMBER_PATTERN.search(css_class)
                if match:
                    return int(match.group(1))
        except ValueError:
            return 0


    @classmethod
    def is_slash_div(div):
        """Determine if this is the slash div (for tried count)"""
        for css_class in div['class']:
            match = SLASH_PATTERN.search(css_class)
            if match:
                return True
        return False


    @classmethod
    def get_level_url(soup, url):
        """Get the bookmark URL for a level"""
        name = soup.find('div', class_='course-title').getText()
        return "[{name}]({url})".format(name=name, url=url)


    @classmethod
    def parse(cls, level_id):
        """Parse level details just given its level ID"""
        url = LEVEL_URL.format(level=level_id)
        page = urllib2.urlopen(url)
        soup = bs4.BeautifulSoup(page, 'html5lib')
        return cls.parse_soup(url, soup)

    @classmethod
    def parse_soup(cls, url_string, soup):
        """Parse a BeautifulSoup object to get level details"""
        liked = 0
        played = 0
        tried = 0.0

        url = cls.get_level_url(soup, url_string)

        liked_divs = soup.find('div', class_='liked-count')
        for div in liked_divs.find_all('div', class_='typography'):
            liked = liked * 10 + cls.get_number(div)

        played_divs = soup.find('div', class_='played-count')
        for div in played_divs.find_all('div', class_='typography'):
            played = played * 10 + cls.get_number(div)

        found_slash = False
        numerator = 0
        denominator = 0
        tried_divs = soup.find('div', class_='tried-count')
        for div in tried_divs.find_all('div', class_='typography'):
            if found_slash:
                denominator = denominator * 10 + cls.get_number(div)
            elif cls.is_slash_div(div):
                found_slash = True
            else:
                numerator = numerator * 10 + cls.get_number(div)

        if denominator == 0:
            tried = 'No tries yet!'
        else:
            tried = 100 * numerator / float(denominator)

        return Level(
            id=id,
            url=url,
            liked=liked,
            played=played,
            tried=tried,
        )


engine = create_engine(os.environ['BOT_DB_NAME'])
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def get_session():
    return Session()


def comment_exists(id):
    session = get_session()
    return session.query(Comment).filter(Comment.id == id).first()


def add_comment(id):
    session = get_session()
    comment = Comment(id=id)
    session.add(comment)
    session.commit()


def user_exists(id):
    session = get_session()
    return session.query(User).filter(User.id == id).first()


def add_user(id):
    session = get_session()
    comment = User(id=id)
    session.add(comment)
    session.commit()
