import os
import sqlite3
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

DATABASE_PATH = Path(__file__).resolve().parent.parent.parent / "neostats.db"


def get_connection():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_connection()

    try:
        if DATABASE_URL:
            connection.cursor().execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    document_name TEXT NOT NULL UNIQUE,
                    document_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
        else:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_name TEXT NOT NULL UNIQUE,
                    document_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

        connection.commit()

    finally:
        connection.close()