import os

# redis config
REDIS_DB_HOST = "127.0.0.1"  # your redis host
REDIS_DB_PWD = os.getenv("REDIS_DB_PWD", "123456")  # your redis password

# mysql config
RELATION_DB_PWD = os.getenv("RELATION_DB_PWD", "123456")  # your relation db password
RELATION_DB_URL = f"mysql://root:{RELATION_DB_PWD}@localhost:3306/media_crawler"

# save data to database option
IS_SAVED_DATABASED = False  # if you want to save data to database, set True
