# This work is licensed under the terms of the MIT license
# db.py
from config import database, host, password, port, user
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
Base = declarative_base()
session_local = sessionmaker(bind=engine)


def init_db():
    import models

    Base.metadata.create_all(engine)
