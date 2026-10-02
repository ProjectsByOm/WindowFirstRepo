from __future__ import annotations

from datetime import datetime

from .db import get_connection


def validate_name(name: str) -> str:
    cleaned = name.strip()
    if len(cleaned) < 3 or not cleaned.replace(" ", "").isalpha():
        raise ValueError("Name must be at least 3 characters and contain only letters.")
    return cleaned


def validate_username(username: str) -> str:
    cleaned = username.strip()
    if len(cleaned) < 3:
        raise ValueError("Username must be at least 3 characters long.")
    return cleaned


def validate_password(password: str) -> str:
    cleaned = password.strip()
    if len(cleaned) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    return cleaned


def validate_mobile(mobile: str) -> str:
    cleaned = mobile.strip()
    if len(cleaned) != 10 or not cleaned.isdigit():
        raise ValueError("Mobile number must contain exactly 10 digits.")
    return cleaned


def validate_amount(amount: int, minimum: int = 1, maximum: int | None = None, message: str | None = None) -> int:
    if amount < minimum:
        raise ValueError(message or "Amount must be greater than zero.")
    if maximum is not None and amount > maximum:
        raise ValueError(message or f"Amount must be less than or equal to {maximum}.")
    return amount


def parse_pin(raw_pin: str) -> int:
    if len(raw_pin) != 4 or not raw_pin.isdigit():
        raise ValueError("PIN must be exactly 4 digits.")
    return int(raw_pin)


def record_transaction(conn, from_account: int | None, to_account: int | None, amount: int, transaction_type: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        INSERT INTO Transactions (FromAccount, ToAccount, AmountTransferred, DateAndTime, Type)
        VALUES (?, ?, ?, ?, ?)
        """,
        (from_account, to_account, amount, timestamp, transaction_type),
    )


def create_account(name: str, username: str, password: str, mobile: str, initial_balance: int) -> int:
    cleaned_name = validate_name(name)
    cleaned_username = validate_username(username)
    cleaned_password = validate_password(password)
    cleaned_mobile = validate_mobile(mobile)
    balance = int(initial_balance)
    if balance < 0 or balance > 100000:
        raise ValueError("Initial deposit must be between 0 and 100000.")

    with get_connection() as conn:
        existing = conn.execute("SELECT 1 FROM Customers WHERE Username = ?", (cleaned_username,)).fetchone()
        if existing:
            raise ValueError("Username already exists. Please choose another one.")

        cursor = conn.execute(
            """
            INSERT INTO Customers (Username, Password, Name, Mobile, Account, Balance)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (cleaned_username, cleaned_password, cleaned_name, cleaned_mobile, 0, balance),
        )
        customer_id = cursor.lastrowid
        account_number = 1000000000 + customer_id

        conn.execute(
            "UPDATE Customers SET Account = ? WHERE Id = ?",
            (account_number, customer_id),
        )

        if balance > 0:
            record_transaction(conn, None, account_number, balance, "Deposit")

    return account_number


def get_customer_by_id(customer_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM Customers WHERE Id = ?", (customer_id,)).fetchone()
        return dict(row) if row else None


def get_customer_by_username(username: str):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM Customers WHERE Username = ?", (username,)).fetchone()
        return dict(row) if row else None


def get_customer_by_account(account_number: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM Customers WHERE Account = ?", (account_number,)).fetchone()
        return dict(row) if row else None


def verify_login(username: str, password: str):
    customer = get_customer_by_username(username)
    if not customer:
        return None
    if customer["Password"] != password:
        return None
    return customer


def create_pin(customer_id: int, new_pin: str) -> None:
    pin_value = parse_pin(new_pin)

    with get_connection() as conn:
        row = conn.execute("SELECT Pin FROM Customers WHERE Id = ?", (customer_id,)).fetchone()
        if row and row["Pin"] is not None:
            raise ValueError("PIN already exists. Use the update PIN option.")
        conn.execute("UPDATE Customers SET Pin = ? WHERE Id = ?", (pin_value, customer_id))


def update_pin(customer_id: int, current_pin: str, new_pin: str) -> None:
    parsed_new_pin = parse_pin(new_pin)

    with get_connection() as conn:
        record = conn.execute("SELECT Pin FROM Customers WHERE Id = ?", (customer_id,)).fetchone()
        if not record or record["Pin"] is None:
            raise ValueError("No PIN has been created yet.")

        if parse_pin(current_pin) != record["Pin"]:
            raise ValueError("Current PIN is incorrect.")

        conn.execute("UPDATE Customers SET Pin = ? WHERE Id = ?", (parsed_new_pin, customer_id))


def check_balance(customer_id: int, pin: str) -> int:
    parsed_pin = parse_pin(pin)
    with get_connection() as conn:
        record = conn.execute("SELECT Pin, Balance FROM Customers WHERE Id = ?", (customer_id,)).fetchone()
        if not record:
            raise ValueError("Account not found.")
        if record["Pin"] is None:
            raise ValueError("PIN has not been created for this account.")
        if parsed_pin != record["Pin"]:
            raise ValueError("Wrong PIN.")
        return record["Balance"]


def deposit(customer_id: int, amount: int) -> int:
    amount = int(amount)
    if amount <= 0:
        raise ValueError("Deposit amount must be greater than zero.")
    if amount > 500000:
        raise ValueError("Deposit amount cannot exceed 500000.")

    with get_connection() as conn:
        record = conn.execute("SELECT Balance FROM Customers WHERE Id = ?", (customer_id,)).fetchone()
        if not record:
            raise ValueError("Account not found.")

        new_balance = record["Balance"] + amount
        conn.execute("UPDATE Customers SET Balance = ? WHERE Id = ?", (new_balance, customer_id))
        account_number = conn.execute("SELECT Account FROM Customers WHERE Id = ?", (customer_id,)).fetchone()["Account"]
        record_transaction(conn, None, account_number, amount, "Deposit")
        return new_balance


def withdraw(customer_id: int, amount: int, pin: str) -> int:
    amount = int(amount)
    if amount <= 0:
        raise ValueError("Withdrawal amount must be greater than zero.")
    if amount > 10000:
        raise ValueError("Withdrawal amount cannot exceed 10000.")

    parsed_pin = parse_pin(pin)

    with get_connection() as conn:
        record = conn.execute("SELECT Pin, Balance, Account FROM Customers WHERE Id = ?", (customer_id,)).fetchone()
        if not record:
            raise ValueError("Account not found.")
        if record["Pin"] is None:
            raise ValueError("PIN not created for this account.")
        if parsed_pin != record["Pin"]:
            raise ValueError("Wrong PIN.")
        if amount > record["Balance"]:
            raise ValueError("Insufficient balance.")

        new_balance = record["Balance"] - amount
        conn.execute("UPDATE Customers SET Balance = ? WHERE Id = ?", (new_balance, customer_id))
        record_transaction(conn, record["Account"], None, amount, "Withdrawal")
        return new_balance


def transfer_money(sender_id: int, recipient_account: int, amount: int, pin: str) -> str:
    amount = int(amount)
    if amount <= 0:
        raise ValueError("Transfer amount must be greater than zero.")
    if amount > 100000:
        raise ValueError("Transfer amount cannot exceed 100000.")

    parsed_pin = parse_pin(pin)

    with get_connection() as conn:
        sender = conn.execute("SELECT Id, Account, Pin, Balance FROM Customers WHERE Id = ?", (sender_id,)).fetchone()
        if not sender:
            raise ValueError("Sender account not found.")
        if sender["Pin"] is None:
            raise ValueError("PIN not created for this account.")
        if parsed_pin != sender["Pin"]:
            raise ValueError("Wrong PIN.")
        if sender["Account"] == recipient_account:
            raise ValueError("You cannot transfer money to your own account.")

        recipient = conn.execute("SELECT Id, Account, Balance FROM Customers WHERE Account = ?", (recipient_account,)).fetchone()
        if not recipient:
            raise ValueError("Recipient account not found.")
        if sender["Balance"] < amount:
            raise ValueError("Insufficient balance for this transfer.")

        new_sender_balance = sender["Balance"] - amount
        new_recipient_balance = recipient["Balance"] + amount

        conn.execute("UPDATE Customers SET Balance = ? WHERE Id = ?", (new_sender_balance, sender["Id"]))
        conn.execute("UPDATE Customers SET Balance = ? WHERE Id = ?", (new_recipient_balance, recipient["Id"]))
        record_transaction(conn, sender["Account"], recipient["Account"], amount, "Transfer")

    return f"Transfer successful. {amount} sent to account {recipient_account}."


def get_transaction_history(account_number: int, limit: int = 10):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM Transactions
            WHERE FromAccount = ? OR ToAccount = ?
            ORDER BY TransactionId DESC
            LIMIT ?
            """,
            (account_number, account_number, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def get_admin_summary():
    with get_connection() as conn:
        total_customers = conn.execute("SELECT COUNT(*) AS count FROM Customers").fetchone()["count"]
        total_balance = conn.execute("SELECT COALESCE(SUM(Balance), 0) AS total FROM Customers").fetchone()["total"]
        recent_transactions = conn.execute(
            "SELECT * FROM Transactions ORDER BY TransactionId DESC LIMIT 10"
        ).fetchall()
        return {
            "total_customers": total_customers,
            "total_balance": total_balance,
            "recent_transactions": [dict(row) for row in recent_transactions],
        }
