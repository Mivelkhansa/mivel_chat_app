# This work is licensed under the terms of the MIT license
# db.py
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# this need to change. this is dangerous
host = os.getenv("MYSQL_HOST", "localhost")
port = os.getenv("MYSQL_PORT", "3307")
user = os.getenv("MYSQL_USER", "user")
password = os.getenv("MYSQL_PASSWORD")
database = os.getenv("MYSQL_DATABASE", "main")


engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
Base = declarative_base()
session_local = sessionmaker(bind=engine)


def init_db():
    import models

    Base.metadata.create_all(engine)
