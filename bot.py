# MarioMaker Reddit Bot
# Description:
#   When activated, search a user's history on /r/MarioMaker
#   to find all levels they have submitted
# Author: Logan Gore
# Date: 2016-02-06
#

import bs4
import os
import praw
import praw.helpers
import re
import sqlalchemy
import sqlalchemy.orm
import time
import urllib2

import OAuth2Util


##############################################################################
# SQLAlchemy setup
class Comment(object):
    pass

db = sqlalchemy.create_engine(os.environ['BOT_DB_NAME'])
metadata = sqlalchemy.MetaData(db)
comments = sqlalchemy.Table('comments', metadata, autoload=True)

commentmapper = sqlalchemy.orm.mapper(Comment, comments)
Session = sqlalchemy.orm.sessionmaker(bind=db)

# Check if the database contains a certain comment ID
def db_contains(id):
    session = Session()
    return session.query(Comment).filter(Comment.id == id).first()


# Add a comment to the database
def db_add(id):
    session = Session()
    c = Comment()
    c.id = id
    session.add(c)
    session.commit()

# End of SQLAlchemy setup
##############################################################################


MARIOMAKER = 'MarioMaker'
USER_MATCH_STRING = '\\+/u/{} (\\w+)'.format(os.environ['BOT_USERNAME'])
USER_PATTERN = re.compile(USER_MATCH_STRING)

LEVEL_MATCH_STRING = '\\w{4}-\\w{4}-\\w{4}-\\w{4}'
LEVEL_PATTERN = re.compile(LEVEL_MATCH_STRING)

NUMBER_MATCH_STRING = 'typography-(\\d)'
NUMBER_PATTERN = re.compile(NUMBER_MATCH_STRING)

SLASH_MATCH_STRING = 'typography-slash'
SLASH_PATTERN = re.compile(SLASH_MATCH_STRING)

URL = 'https://supermariomakerbookmark.nintendo.net/courses/{level}'

r = praw.Reddit(user_agent=os.environ['BOT_USER_AGENT'])
o = OAuth2Util.OAuth2Util(r)
o.refresh(force=True)


# Return the MarioMaker levels posted in a comment
def get_levels(comment):
    return re.findall(LEVEL_PATTERN, comment.body)


# Return the levels that a certain user has posted
def get_posted_levels(username):
    time.sleep(2)
    user = r.get_redditor(username)
    res = set()

    time.sleep(2)
    comments_gen = user.get_comments(limit=100)
    for comment in comments_gen:
        if comment.subreddit.display_name.lower() == MARIOMAKER.lower():
            levels = get_levels(comment)
            for level in levels:
                res.add(level)

    return res


# Find out which user's levels is being requested (if any)
def get_requested_user(comment):
    match = USER_PATTERN.search(comment.body)
    if match:
        return match.group(1)
    return None


# Parse a number from a CSS class on a div
def get_number(div):
    try:
        for css_class in div['class']:
            match = NUMBER_PATTERN.search(css_class)
            if match:
                return int(match.group(1))
    except ValueError:
        return 0


# Determine if this is the slash div (for tried count)
def is_slash_div(div):
    for css_class in div['class']:
        match = SLASH_PATTERN.search(css_class)
        if match:
            return True
    return False

# Get the bookmark URL for a level
def get_level_url(level):
    url = URL.format(level=level)
    return "[{id}]({url})".format(id=level, url=url)


# Get details from a MarioMaker level from the bookmarks site
def get_level_details(level):
    details = {
        # THIS url has already been formatted for reddit, do not use urlopen
        'url': get_level_url(level),
        'liked': 0,
        'played': 0,
        'tried': 0.0,
    }
    found_slash = False
    numerator = 0
    denominator = 0

    try:
        page = urllib2.urlopen(URL.format(level=level))
        soup = bs4.BeautifulSoup(page, 'html5lib')
        for _div in soup.find_all('div', class_='liked-count'):
            for div in _div.find_all('div', class_='typography'):
                details['liked'] = details['liked'] * 10 + get_number(div)

        for _div in soup.find_all('div', class_='played-count'):
            for div in _div.find_all('div', class_='typography'):
                details['played'] = details['played'] * 10 + get_number(div)

        for _div in soup.find_all('div', class_='tried-count'):
            for div in _div.find_all('div', class_='typography'):
                if found_slash:
                    denominator = denominator * 10 + get_number(div)
                elif is_slash_div(div):
                    found_slash = True
                else:
                    numerator = numerator * 10 + get_number(div)
        if denominator == 0:
            details['tried'] = 'No tries yet!'
        else:
            details['tried'] = 100 * numerator / float(denominator)
    except urllib2.HTTPError:
        pass
    return details


# Return a pretty formatted level string for a table row
def format_level(level):
    details = get_level_details(level)
    # Round the completion rate to 2 decimal places
    tried = details['tried']
    star = details['tried']
    try:
        tried = "{0:.2f}".format(tried)
        star = "{0:.2f}".format(
            100 * float(details['liked']) / details['played'],
        )
    except:
        pass

    return "{url}|{liked}|{played}|{tried}|{star}\n".format(
        url=details['url'],
        liked=details['liked'],
        played=details['played'],
        tried=tried,
        star=star,
    )


# Reply to a comment with the given levels
def make_reply(comment, username, levels):
    reply_string = "Couldn't find any recent level posts from {name}".format(
        name=username,
    )

    if levels:
        reply_string = (
            "Try checking out some of these "
            "other recent levels posted by {name}!\n\n".format(name=username)
        )
        reply_string += "URL|Stars|Plays|Completion %|Star %\n"
        reply_string += ":--|:--|:--|:--|:--\n"
        for level in levels:
            reply_string += format_level(level)

    reply_string += "\n\n*****\n\n"
    reply_string += "For questions about this bot, contact /u/Virule"
    time.sleep(2)
    comment.reply(reply_string)


# Start the bot
def main():
    print('Bot started.')
    while True:
        # Don't get rate limited!
        time.sleep(2)

        comments = praw.helpers.comment_stream(r, MARIOMAKER, limit=100)
        for comment in comments:
            if not db_contains(comment.id):
                user = get_requested_user(comment)
                if user:
                    print('\nUser requested: {}'.format(user))
                    levels = get_posted_levels(user)
                    print('Found {} levels'.format(len(levels)))
                    # Don't get rate limited!
                    time.sleep(2)
                    make_reply(comment, user, levels)
                    print('Sent reply!')
                    db_add(comment.id)


if __name__ == '__main__':
    main()
