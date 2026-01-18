# This work is licensed under the terms of the MIT license
import os

from dotenv import load_dotenv

env_path = "backend/.env"

if os.path.exists(env_path):
    load_dotenv(env_path)

host = os.getenv("MYSQL_HOST", "localhost")
port = os.getenv("MYSQL_PORT", "3307")
user = os.getenv("MYSQL_USER", "user")
password = os.getenv("MYSQL_PASSWORD")
database = os.getenv("MYSQL_DATABASE", "main")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
JWT_ACCESS_SECRET_KEY = os.getenv("JWT_ACCESS_SECRET_KEY", "access-secret")
JWT_REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", "refresh-secret")
JWT_ACCESS_EXPIRATION = int(os.getenv("JWT_ACCESS_EXPIRATION", 600))
JWT_REFRESH_EXPIRATION = int(os.getenv("JWT_REFRESH_EXPIRATION", 3600))
JWT_ALGORITHM = "HS256"
