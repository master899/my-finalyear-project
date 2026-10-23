import os
from dotenv import load_dotenv

load_dotenv()


def get_env_value(primary_key, aliases=None, default=None):
    keys = [primary_key] + (aliases or [])
    for key in keys:
        value = os.environ.get(key)
        if value not in (None, ""):
            return value
    return default


class Config:
    SECRET_KEY = get_env_value("SECRET_KEY", default="change-this-secret-key")
    MYSQL_HOST = get_env_value("DB_HOST", ["MYSQL_HOST"], "127.0.0.1")
    MYSQL_USER = get_env_value("DB_USER", ["MYSQL_USER"], "root")
    MYSQL_PASSWORD = get_env_value("DB_PASSWORD", ["MYSQL_PASSWORD"], "")
    MYSQL_DB = get_env_value("DB_NAME", ["MYSQL_DB"], "tb_cdss")
