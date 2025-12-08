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
