import os
from typing import Dict
from dotenv import load_dotenv


def load_config() -> Dict[str, str]:
    load_dotenv()
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", 3306)),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", "password"),
        "db": os.getenv("MYSQL_DATABASE"),
        "maxsize": os.getenv("MYSQL_MAXSIZE", 2),
        "role": os.getenv("MYSQL_ROLE", "r")
    }


# 权限控制
PERMISSIONS = {
    "r": ["SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "USE"],
    "w": ["SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "INSERT", "UPDATE", "DELETE", "USE"],
    "a": ["SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "INSERT", "UPDATE", "DELETE",
          "CREATE", "ALTER", "DROP", "TRUNCATE", "USE"]
}
