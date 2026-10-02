from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

DB_PATH = Path(__file__).resolve().parent.parent / "Bank.db"


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def initialize_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS Customers(
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                Username TEXT UNIQUE NOT NULL,
                Password TEXT NOT NULL,
                Name TEXT NOT NULL,
                Mobile TEXT NOT NULL,
                Account INTEGER UNIQUE NOT NULL,
                Pin INTEGER,
                Balance INTEGER NOT NULL DEFAULT 0 CHECK(Balance >= 0)
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS Transactions(
                TransactionId INTEGER PRIMARY KEY AUTOINCREMENT,
                FromAccount INTEGER,
                ToAccount INTEGER,
                AmountTransferred INTEGER NOT NULL CHECK(AmountTransferred > 0),
                DateAndTime TEXT NOT NULL,
                Type TEXT NOT NULL DEFAULT 'Transfer',
                FOREIGN KEY (FromAccount) REFERENCES Customers(Account),
                FOREIGN KEY (ToAccount) REFERENCES Customers(Account)
            );
            """
        )

        transaction_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(Transactions)").fetchall()
        }
        if "Type" not in transaction_columns:
            conn.execute(
                "ALTER TABLE Transactions ADD COLUMN Type TEXT NOT NULL DEFAULT 'Transfer'"
            )
