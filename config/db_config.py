import os
import dotenv

dotenv.load_dotenv()

# redis config
REDIS_DB_HOST = "127.0.0.1"  # your redis host
REDIS_DB_PWD = os.getenv("REDIS_DB_PWD", "123456")  # your redis password

# mysql config
RELATION_DB_PWD = os.getenv("RELATION_DB_PWD", "123456")
RELATION_DB_USER = os.getenv("RELATION_DB_USER", "root")
RELATION_DB_HOST = os.getenv("RELATION_DB_HOST", "localhost")
RELATION_DB_PORT = os.getenv("RELATION_DB_PORT", "3306")
RELATION_DB_NAME = os.getenv("RELATION_DB_NAME", "media_crawler")


RELATION_DB_URL = f"mysql://{RELATION_DB_USER}:{RELATION_DB_PWD}@{RELATION_DB_HOST}:{RELATION_DB_PORT}/{RELATION_DB_NAME}"

# sqlite3 config
# RELATION_DB_URL = f"sqlite://data/media_crawler.sqlite"
