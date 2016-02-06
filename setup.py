import os
from sqlalchemy import *

db = create_engine(os.environ['BOT_DB_NAME'])
metadata = MetaData(db)
comments = Table(
    'comments',
    metadata,
    Column('id', String(16), primary_key=True),
)
comments.create()
