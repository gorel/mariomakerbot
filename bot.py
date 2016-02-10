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
import time

import OAuth2Util

import models


MARIOMAKER = 'MarioMaker'
USER_MATCH_STRING = '\\+/u/{} ([\\w-]+)'.format(os.environ['BOT_USERNAME'])
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
    # Don't get rate limited!
    time.sleep(2)
    user = r.get_redditor(username)
    level_set = set()

    # Don't get rate limited!
    time.sleep(2)
    comments_gen = user.get_comments(limit=100)
    try:
        for comment in comments_gen:
            if comment.subreddit.display_name.lower() == MARIOMAKER.lower():
                levels = get_levels(comment)
                for level in levels:
                    level_set.add(level)
    except:
        pass

    res = []
    for level_id in level_set:
        level = models.Level.parse(level_id)
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
    reply_string = "Couldn't find any levels by {name}".format(name=username)

    if levels:
        reply_string = (
            "Here are the {n} most recent "
            "levels uploaded by {name}!\n\n".format(
                n=len(levels),
                name=models.maker_url(username),
            )
        )
        reply_string += "URL|Stars|Plays|Completion %|Star %\n"
        reply_string += ":--|:--|:--|:--|:--\n"
        for level in levels:
            reply_string += level.format()

    reply_string += "\n\n*****\n\n"
    reply_string += "For questions about this bot, contact /u/Virule"
    time.sleep(2)
    while True:
        try:
            comment.reply(reply_string)
            break
        except:
            print("Rate limit -- sleeping 5 seconds")
            time.sleep(5)


# Start the bot
def main():
    print('Bot started.')
    while True:
        try:
            print("Get new comments")
            comments = praw.helpers.comment_stream(r, MARIOMAKER, limit=100)
            for comment in comments:
                if not models.comment_exists(comment.id):
                    user = get_requested_user(comment)
                    if user:
                        print('\nUser requested: {}'.format(user))
                        level_ids = models.Level.get_level_ids(user)
                        print("Parsing levels from MM site")
                        levels = []
                        for level_id in level_ids:
                            level = models.Level.parse(level_id)
                            if level:
                                levels.append(level)
                        print('Found {} levels'.format(len(levels)))
                        # Don't get rate limited!
                        time.sleep(5)
                        make_reply(comment, user, levels)
                        print('Sent reply!')
                        models.add_comment(comment.id)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print("Error getting comments. Try again")
            print("Error message: {}".format(str(e)))


if __name__ == '__main__':
    main()
