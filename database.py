import mysql.connector
from mysql.connector import pooling

dbconfig = {
    "user": "gutenberg-db",
    "password": "prajwalsql123",
    "host": "34.46.228.40",
    "database": "BOOKS_DB",
    "raise_on_warnings": True,
}

connection_pool = pooling.MySQLConnectionPool(
    pool_name="mypool", pool_size=5, **dbconfig
)
