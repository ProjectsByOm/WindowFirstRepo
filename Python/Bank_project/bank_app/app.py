from __future__ import annotations

from .db import initialize_db
from .services import (
    check_balance,
    create_account,
    create_pin,
    deposit,
    get_admin_summary,
    get_customer_by_id,
    transfer_money,
    update_pin,
    verify_login,
    withdraw,
    get_transaction_history,
)
from .ui import banner, print_admin_summary, print_customer_details, print_customer_menu, print_main_menu, print_transaction_rows, separator


def read_input(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        print("\nInput stream closed. Exiting gracefully.")
        raise SystemExit(0)


class BankApp:
    def __init__(self) -> None:
        initialize_db()

    def run(self) -> None:
        banner()
        while True:
            print_main_menu()
            try:
                choice = int(read_input("Choice (1, 2, 3, 777): ").strip())
            except ValueError:
                print("Invalid input. Please enter a valid number.")
                continue

            if choice == 1:
                self.create_account_flow()
            elif choice == 2:
                self.login_flow()
            elif choice == 3:
                print("\n/*/*/*/============ Thank you for using the program ============/*/*/*/")
                break
            elif choice == 777:
                self.admin_login_flow()
            else:
                print("Invalid input. Please enter a number between 1 and 3 or 777.")

    def create_account_flow(self) -> None:
        print("\n")
        separator("-")
        print("                        ACCOUNT CREATION")
        separator("-")

        try:
            name = read_input("    Name: ").strip()
            username = read_input("    Username: ").strip()
            password = read_input("    Password: ").strip()
            mobile = read_input("    Mobile No.: ").strip()
            initial_balance = int(read_input("    Make first deposit: ").strip())
            account_number = create_account(name, username, password, mobile, initial_balance)
            print("\nAccount created successfully.")
            print(f"Your account number is: {account_number}")
            separator("_")
        except ValueError as exc:
            print(f"\n[ERROR] {exc}")

    def login_flow(self) -> None:
        print("\n")
        separator("-")
        print("                        LOGIN SECTION")
        separator("-")

        username = read_input("  Username: ").strip()
        password = read_input("  Password: ").strip()

        customer = verify_login(username, password)
        if customer is None:
            print("\n[ERROR] Invalid username or password.")
            return

        self.customer_dashboard(customer)

    def customer_dashboard(self, customer: dict) -> None:
        customer = get_customer_by_id(customer["Id"]) or customer
        while True:
            print_customer_details(customer)
            print_customer_menu()

            try:
                choice = int(read_input("Choose (1,2,3,4,5,6,7,8): ").strip())
            except ValueError:
                print("[ERROR] Invalid input. Please enter a valid number.")
                continue

            if choice == 1:
                self.create_pin_flow(customer)
            elif choice == 2:
                self.update_pin_flow(customer)
            elif choice == 3:
                self.check_balance_flow(customer)
            elif choice == 4:
                self.deposit_flow(customer)
            elif choice == 5:
                self.withdraw_flow(customer)
            elif choice == 6:
                self.transfer_flow(customer)
            elif choice == 7:
                self.transaction_history_flow(customer)
            elif choice == 8:
                print("\nLogging out...")
                break
            else:
                print("[ERROR] Please choose a number between 1 and 8.")

            customer = get_customer_by_id(customer["Id"]) or customer

    def create_pin_flow(self, customer: dict) -> None:
        if customer.get("Pin") is not None:
            print("\n[INFO] A PIN already exists.")
            choice = read_input("Do you want to update it instead? (y/n): ").strip().lower()
            if choice not in {"y", "yes"}:
                return
            self.update_pin_flow(customer)
            return

        try:
            new_pin = read_input("New PIN (4 digits): ").strip()
            create_pin(customer["Id"], new_pin)
            print("\n[OK] PIN created successfully.")
        except ValueError as exc:
            print(f"\n[ERROR] {exc}")

    def update_pin_flow(self, customer: dict) -> None:
        try:
            current_pin = read_input("Current PIN: ").strip()
            new_pin = read_input("New PIN (4 digits): ").strip()
            update_pin(customer["Id"], current_pin, new_pin)
            print("\n[OK] PIN updated successfully.")
        except ValueError as exc:
            print(f"\n[ERROR] {exc}")

    def check_balance_flow(self, customer: dict) -> None:
        try:
            pin = read_input("PIN: ").strip()
            balance = check_balance(customer["Id"], pin)
            print(f"\nCurrent Balance: {balance}")
        except ValueError as exc:
            print(f"\n[ERROR] {exc}")

    def deposit_flow(self, customer: dict) -> None:
        try:
            amount = int(read_input("Amount to deposit: ").strip())
            new_balance = deposit(customer["Id"], amount)
            print(f"\n[OK] Deposit successful. New balance: {new_balance}")
        except ValueError as exc:
            print(f"\n[ERROR] {exc}")

    def withdraw_flow(self, customer: dict) -> None:
        try:
            pin = read_input("PIN: ").strip()
            amount = int(read_input("Amount to withdraw: ").strip())
            new_balance = withdraw(customer["Id"], amount, pin)
            print(f"\n[OK] Withdrawal successful. New balance: {new_balance}")
        except ValueError as exc:
            print(f"\n[ERROR] {exc}")

    def transfer_flow(self, customer: dict) -> None:
        try:
            recipient_account = int(read_input("Recipient account number: ").strip())
            amount = int(read_input("Amount to transfer: ").strip())
            pin = read_input("PIN: ").strip()
            message = transfer_money(customer["Id"], recipient_account, amount, pin)
            print(f"\n[OK] {message}")
        except ValueError as exc:
            print(f"\n[ERROR] {exc}")

    def transaction_history_flow(self, customer: dict) -> None:
        rows = get_transaction_history(customer["Account"], limit=10)
        print("\nRecent Transactions:")
        print_transaction_rows(rows)

    def admin_login_flow(self) -> None:
        username = read_input("Admin username: ").strip()
        password = read_input("Admin password: ").strip()

        if username == "admin" and password == "admin123":
            summary = get_admin_summary()
            print_admin_summary(summary)
            return

        print("\n[ERROR] Invalid admin credentials.")


def run_app() -> None:
    BankApp().run()
