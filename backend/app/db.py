# This work is licensed under the terms of the MIT license
# db.py
import time

from config import database, host, password, port, user
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
Base = declarative_base()
session_local = sessionmaker(bind=engine)


# i hate this function
# note: just a temporary function for local developtment never actually use in prod
def init_db():
    import models

    attempts = 0
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        while attempts < 50:
            try:
                Base.metadata.create_all(engine)
                break
            except Exception:
                attempts += 1
                time.sleep(1)
        else:
            raise e
