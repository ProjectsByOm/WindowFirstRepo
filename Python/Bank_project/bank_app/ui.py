def separator(symbol: str = "=", length: int = 67) -> None:
    print(symbol * length)


def banner() -> None:
    separator("=")
    print("                      BANK MANAGEMENT SYSTEM")
    separator("=")


def print_main_menu() -> None:
    print("\n    1. Create Account")
    print("    2. Login")
    print("    3. Exit")
    print("    777. Admin Login\n")


def print_customer_menu() -> None:
    print("\n   1. Create New PIN")
    print("   2. Update PIN")
    print("   3. Check Balance")
    print("   4. Deposit")
    print("   5. Withdraw")
    print("   6. Transfer Money")
    print("   7. Transaction History")
    print("   8. Logout\n")


def print_customer_details(customer: dict) -> None:
    separator("=")
    print(f"                   Welcome, {customer['Name']}")
    separator("-")
    print(f"  ID: {customer['Id']}")
    print(f"  Username: {customer['Username']}")
    print(f"  Mobile: {customer['Mobile']}")
    print(f"  Account: {customer['Account']}")
    print(f"  Balance: {customer['Balance']}")
    separator("=")


def print_transaction_rows(rows: list[dict]) -> None:
    if not rows:
        print("  No transactions found.")
        return

    for entry in rows:
        direction = ""
        if entry["Type"] == "Deposit":
            direction = f"Received {entry['AmountTransferred']}"
        elif entry["Type"] == "Withdrawal":
            direction = f"Withdrawn {entry['AmountTransferred']}"
        elif entry["Type"] == "Transfer":
            if entry["FromAccount"] is not None and entry["ToAccount"] is not None:
                direction = f"Transferred {entry['AmountTransferred']}"
            else:
                direction = f"Transfer {entry['AmountTransferred']}"
        else:
            direction = f"{entry['Type']} {entry['AmountTransferred']}"

        from_account = entry["FromAccount"] if entry["FromAccount"] is not None else "-"
        to_account = entry["ToAccount"] if entry["ToAccount"] is not None else "-"
        print(f"  [{entry['DateAndTime']}] {entry['Type']}: {direction} | From: {from_account} | To: {to_account}")


def print_admin_summary(summary: dict) -> None:
    separator("=")
    print("                     ADMIN DASHBOARD")
    separator("-")
    print(f"  Total Customers: {summary['total_customers']}")
    print(f"  Total Balance: {summary['total_balance']}")
    print("  Recent Transactions:")
    print_transaction_rows(summary["recent_transactions"])
    separator("=")
