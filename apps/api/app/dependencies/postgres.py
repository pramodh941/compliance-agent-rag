import psycopg2
import os

def get_postgres_connection():
    conn = psycopg2.connect(
        host="postgres",
        port=5432,
        user="admin",
        password="admin",
        dbname="compliance"
    )
    return conn