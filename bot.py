# MarioMaker Reddit Bot
# Description:
#   When activated, search a user's history on /r/MarioMaker
#   to find all levels they have submitted
# Author: Logan Gore
# Date: 2016-02-06
#

import os
import praw
import praw.helpers
import re
import sqlalchemy
import sqlalchemy.orm

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

r = praw.Reddit(user_agent=os.environ['BOT_USER_AGENT'])
o = OAuth2Util.OAuth2Util(r)
o.refresh(force=True)


# Return the MarioMaker levels posted in a comment
def get_levels(comment):
    return re.findall(LEVEL_PATTERN, comment.body)


# Return the levels that a certain user has posted
def get_posted_levels(username):
    user = r.get_redditor(username)
    res = []

    comments_gen = user.get_comments()
    for comment in comments_gen:
        if comment.subreddit.display_name.lower() == MARIOMAKER.lower():
            levels = get_levels(comment)
            for level in levels:
                res.append(level)

    return res


# Find out which user's levels is being requested (if any)
def get_requested_user(comment):
    match = USER_PATTERN.search(comment.body)
    if match:
        return match.group(1)
    return None


# Reply to a comment with the given levels
def make_reply(comment, username, levels):
    if levels:
        reply_string = (
            "Try checking out some of these "
            "other levels from {}!\n".format(username)
        )
        for level in levels:
            reply_string += '\n* {}  '.format(level)

        comment.reply(reply_string)
    else:
        comment.reply(
            "Couldn't find any recent level posts from {}".format(username)
        )


# Start the bot
def main():
    print('Bot started.')
    for comment in praw.helpers.comment_stream(r, MARIOMAKER, limit=100):
        if not db_contains(comment.id):
            user = get_requested_user(comment)
            if user:
                print('\nUser requested: {}'.format(user))
                levels = get_posted_levels(user)
                print('Found {} levels'.format(len(levels)))
                make_reply(comment, user, levels)
                print('Sent reply!')
                db_add(comment.id)


if __name__ == '__main__':
    main()
