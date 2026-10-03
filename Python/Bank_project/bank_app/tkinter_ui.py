from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from .db import initialize_db
from .services import (
    check_balance,
    create_account,
    create_pin,
    deposit,
    get_admin_summary,
    get_customer_by_id,
    get_transaction_history,
    transfer_money,
    update_pin,
    verify_login,
    withdraw,
)


BACKGROUND = "#f3f6f4"
SURFACE = "#ffffff"
INK = "#17231f"
MUTED = "#6f7d76"
GREEN = "#167653"
GREEN_DARK = "#105c40"
PALE_GREEN = "#e8f3ed"
BORDER = "#e1e8e3"


def _read_integer(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a whole number.") from exc


class BankTkApp:
    def __init__(self, root: tk.Tk) -> None:
        initialize_db()
        self.root = root
        self.customer: dict | None = None
        self.root.title("Om's Bank Of india")
        self.root.geometry("1120x760")
        self.root.minsize(900, 650)
        self.root.configure(bg=BACKGROUND)

        self.style = ttk.Style(root)
        self.style.configure(
            "Bank.Treeview",
            background=SURFACE,
            fieldbackground=SURFACE,
            foreground=INK,
            rowheight=34,
            borderwidth=0,
        )
        self.style.configure(
            "Bank.Treeview.Heading",
            background=BACKGROUND,
            foreground=MUTED,
            font=("Segoe UI", 9, "bold"),
            relief="flat",
        )
        self.style.map("Bank.Treeview", background=[("selected", PALE_GREEN)])
        self.show_welcome()

    def _clear(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()

    def _button(
        self,
        parent: tk.Widget,
        text: str,
        command: Callable[[], None],
        *,
        primary: bool = False,
        width: int | None = None,
    ) -> tk.Button:
        color = GREEN if primary else SURFACE
        foreground = SURFACE if primary else INK
        active = GREEN_DARK if primary else PALE_GREEN
        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg=foreground,
            activebackground=active,
            activeforeground=foreground,
            relief="flat",
            bd=0,
            padx=18,
            pady=11,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            width=width,
        )
        return button

    def _field(
        self,
        parent: tk.Widget,
        label: str,
        *,
        show: str | None = None,
    ) -> tk.StringVar:
        tk.Label(
            parent,
            text=label,
            bg=SURFACE,
            fg=INK,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(12, 6))
        value = tk.StringVar()
        tk.Entry(
            parent,
            textvariable=value,
            show=show or "",
            bg="#fbfcfb",
            fg=INK,
            insertbackground=INK,
            relief="solid",
            bd=1,
            highlightthickness=0,
            font=("Segoe UI", 11),
        ).pack(fill="x", ipady=10)
        return value

    def _brand_header(self, parent: tk.Widget) -> None:
        header = tk.Frame(parent, bg=BACKGROUND)
        header.pack(fill="x", pady=(0, 24))
        tk.Label(
            header,
            text="NORTHSTAR",
            bg=BACKGROUND,
            fg=GREEN,
            font=("Segoe UI", 17, "bold"),
        ).pack(side="left")
        tk.Label(
            header,
            text="BANKING, MADE CLEAR",
            bg=BACKGROUND,
            fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(12, 0), pady=(5, 0))

    def show_welcome(self) -> None:
        self.customer = None
        self._clear()
        outer = tk.Frame(self.root, bg=BACKGROUND)
        outer.pack(fill="both", expand=True, padx=38, pady=30)
        self._brand_header(outer)

        content = tk.Frame(outer, bg=BACKGROUND)
        content.pack(fill="both", expand=True)
        intro = tk.Frame(content, bg=GREEN, padx=34, pady=38)
        intro.pack(side="left", fill="both", expand=True, padx=(0, 22))
        tk.Label(
            intro,
            text="Your money.\nYour next move.",
            bg=GREEN,
            fg=SURFACE,
            font=("Segoe UI", 30, "bold"),
            justify="left",
        ).pack(anchor="w", pady=(20, 14))
        tk.Label(
            intro,
            text="A simple place to manage your account, move money, and keep track of every transaction.",
            bg=GREEN,
            fg="#d9eee4",
            font=("Segoe UI", 12),
            wraplength=340,
            justify="left",
        ).pack(anchor="w")
        tk.Label(
            intro,
            text="SECURE  /  SIMPLE  /  ALWAYS YOURS",
            bg=GREEN,
            fg="#c0e2d1",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", side="bottom", pady=(30, 0))

        self.welcome_card = tk.Frame(
            content, bg=SURFACE, padx=34, pady=30, highlightbackground=BORDER, highlightthickness=1
        )
        self.welcome_card.pack(side="right", fill="both", expand=True)
        self.show_login_form()

    def show_login_form(self) -> None:
        for child in self.welcome_card.winfo_children():
            child.destroy()
        tk.Label(
            self.welcome_card,
            text="Welcome back",
            bg=SURFACE,
            fg=INK,
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")
        tk.Label(
            self.welcome_card,
            text="Sign in to continue to your account.",
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(6, 12))
        username = self._field(self.welcome_card, "Username")
        password = self._field(self.welcome_card, "Password", show="*")

        def login() -> None:
            customer = verify_login(username.get().strip(), password.get())
            if customer is None:
                messagebox.showerror("Sign in failed", "That username and password do not match.")
                return
            self.customer = customer
            self.show_customer_dashboard()

        self._button(self.welcome_card, "Sign in", login, primary=True).pack(fill="x", pady=(22, 12))
        links = tk.Frame(self.welcome_card, bg=SURFACE)
        links.pack(fill="x")
        self._text_link(links, "Create an account", self.show_signup_form).pack(side="left")
        self._text_link(links, "Admin access", self.show_admin_login).pack(side="right")

    def _text_link(self, parent: tk.Widget, text: str, command: Callable[[], None]) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=SURFACE,
            fg=GREEN,
            activebackground=SURFACE,
            activeforeground=GREEN_DARK,
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )

    def show_signup_form(self) -> None:
        for child in self.welcome_card.winfo_children():
            child.destroy()
        tk.Label(
            self.welcome_card,
            text="Open an account",
            bg=SURFACE,
            fg=INK,
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")
        tk.Label(
            self.welcome_card,
            text="Enter your details to get started.",
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(6, 2))
        fields = {
            "name": self._field(self.welcome_card, "Full name"),
            "username": self._field(self.welcome_card, "Username"),
            "password": self._field(self.welcome_card, "Password (at least 8 characters)", show="*"),
            "mobile": self._field(self.welcome_card, "Mobile number"),
            "balance": self._field(self.welcome_card, "Initial deposit (0 to 100000)"),
        }

        def submit() -> None:
            try:
                account_number = create_account(
                    fields["name"].get(),
                    fields["username"].get(),
                    fields["password"].get(),
                    fields["mobile"].get(),
                    _read_integer(fields["balance"].get(), "Initial deposit"),
                )
            except ValueError as exc:
                messagebox.showerror("Could not create account", str(exc))
                return
            messagebox.showinfo(
                "Account created",
                f"Your account is ready.\nAccount number: {account_number}",
            )
            self.show_login_form()

        self._button(self.welcome_card, "Create account", submit, primary=True).pack(
            fill="x", pady=(20, 12)
        )
        self._text_link(self.welcome_card, "Back to sign in", self.show_login_form).pack(anchor="w")

    def show_admin_login(self) -> None:
        for child in self.welcome_card.winfo_children():
            child.destroy()
        tk.Label(
            self.welcome_card,
            text="Admin access",
            bg=SURFACE,
            fg=INK,
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")
        tk.Label(
            self.welcome_card,
            text="Sign in with your administrator credentials.",
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(6, 12))
        username = self._field(self.welcome_card, "Username")
        password = self._field(self.welcome_card, "Password", show="*")

        def submit() -> None:
            if username.get().strip() == "admin" and password.get() == "admin123":
                self.show_admin_dashboard()
            else:
                messagebox.showerror("Sign in failed", "Invalid administrator credentials.")

        self._button(self.welcome_card, "Sign in as admin", submit, primary=True).pack(
            fill="x", pady=(22, 12)
        )
        self._text_link(self.welcome_card, "Back to customer sign in", self.show_login_form).pack(
            anchor="w"
        )

    def show_customer_dashboard(self) -> None:
        if self.customer is None:
            self.show_welcome()
            return
        self._clear()
        shell = tk.Frame(self.root, bg=BACKGROUND)
        shell.pack(fill="both", expand=True)
        sidebar = tk.Frame(shell, bg="#123d2e", width=220, padx=18, pady=24)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(
            sidebar,
            text="NORTHSTAR",
            bg="#123d2e",
            fg=SURFACE,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", padx=8, pady=(4, 30))
        nav_items = [
            ("Overview", self.show_overview),
            ("Check balance", self.show_balance_form),
            ("Deposit", self.show_deposit_form),
            ("Withdraw", self.show_withdraw_form),
            ("Transfer", self.show_transfer_form),
            ("Transactions", self.show_history),
            ("Manage PIN", self.show_pin_form),
        ]
        for label, command in nav_items:
            tk.Button(
                sidebar,
                text=label,
                command=command,
                anchor="w",
                bg="#123d2e",
                fg="#e4f1e9",
                activebackground="#1c5940",
                activeforeground=SURFACE,
                relief="flat",
                bd=0,
                padx=12,
                pady=12,
                cursor="hand2",
                font=("Segoe UI", 10),
            ).pack(fill="x", pady=2)
        self._button(sidebar, "Sign out", self.show_welcome).pack(side="bottom", fill="x", pady=(12, 0))

        main = tk.Frame(shell, bg=BACKGROUND, padx=32, pady=26)
        main.pack(side="right", fill="both", expand=True)
        topbar = tk.Frame(main, bg=BACKGROUND)
        topbar.pack(fill="x", pady=(0, 22))
        tk.Label(
            topbar,
            text=f"Hello, {self.customer['Name']}",
            bg=BACKGROUND,
            fg=INK,
            font=("Segoe UI", 21, "bold"),
        ).pack(side="left")
        tk.Label(
            topbar,
            text=f"ACCOUNT  {self.customer['Account']}",
            bg=BACKGROUND,
            fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="right", pady=(7, 0))
        self.page_body = tk.Frame(main, bg=BACKGROUND)
        self.page_body.pack(fill="both", expand=True)
        self.show_overview()

    def _refresh_customer(self) -> bool:
        if self.customer is None:
            return False
        refreshed = get_customer_by_id(self.customer["Id"])
        if refreshed is None:
            self.customer = None
            messagebox.showerror("Account unavailable", "This account could not be found.")
            self.show_welcome()
            return False
        self.customer = refreshed
        return True

    def _clear_page(self) -> None:
        for child in self.page_body.winfo_children():
            child.destroy()

    def _panel(self, title: str, subtitle: str) -> tk.Frame:
        self._clear_page()
        panel = tk.Frame(
            self.page_body,
            bg=SURFACE,
            padx=28,
            pady=26,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        panel.pack(fill="both", expand=True, anchor="n")
        tk.Label(
            panel,
            text=title,
            bg=SURFACE,
            fg=INK,
            font=("Segoe UI", 19, "bold"),
        ).pack(anchor="w")
        tk.Label(
            panel,
            text=subtitle,
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 14))
        return panel

    def show_overview(self) -> None:
        if self.customer is None:
            self.show_welcome()
            return
        panel = self._panel("Account overview", "A quick look at your account.")
        card = tk.Frame(panel, bg=PALE_GREEN, padx=24, pady=22)
        card.pack(fill="x", pady=(6, 18))
        tk.Label(
            card,
            text="CURRENT BALANCE",
            bg=PALE_GREEN,
            fg=GREEN_DARK,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")
        tk.Label(
            card,
            text=f"{self.customer['Balance']:,}",
            bg=PALE_GREEN,
            fg=INK,
            font=("Segoe UI", 30, "bold"),
        ).pack(anchor="w", pady=(5, 0))
        tk.Label(
            panel,
            text=f"Account holder: {self.customer['Name']}\n"
            f"Username: {self.customer['Username']}\n"
            f"Mobile: {self.customer['Mobile']}",
            bg=SURFACE,
            fg=MUTED,
            justify="left",
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(4, 20))
        quick_actions = tk.Frame(panel, bg=SURFACE)
        quick_actions.pack(anchor="w")
        self._button(quick_actions, "Deposit money", self.show_deposit_form, primary=True).pack(
            side="left", padx=(0, 10)
        )
        self._button(quick_actions, "Transfer", self.show_transfer_form).pack(side="left")

    def _show_form(
        self,
        title: str,
        subtitle: str,
        field_specs: list[tuple[str, str, str | None]],
        submit_label: str,
        submit_action: Callable[[dict[str, str]], None],
    ) -> None:
        panel = self._panel(title, subtitle)
        form = tk.Frame(panel, bg=SURFACE, width=480)
        form.pack(anchor="nw", fill="x", pady=(5, 0))
        form.pack_propagate(False)
        values: dict[str, tk.StringVar] = {}
        for key, label, mask in field_specs:
            values[key] = self._field(form, label, show=mask)

        def submit() -> None:
            try:
                submit_action({key: value.get().strip() for key, value in values.items()})
            except ValueError as exc:
                messagebox.showerror("Action could not be completed", str(exc))

        self._button(form, submit_label, submit, primary=True).pack(anchor="w", pady=(22, 0))

    def _complete_action(self, message: str) -> None:
        if self._refresh_customer():
            self.show_overview()
            messagebox.showinfo("Completed", message)

    def show_balance_form(self) -> None:
        if self.customer is None:
            return
        customer_id = self.customer["Id"]

        def submit(values: dict[str, str]) -> None:
            balance = check_balance(customer_id, values["pin"])
            messagebox.showinfo("Current balance", f"Your balance is {balance:,}.")

        self._show_form(
            "Check balance",
            "Verify your PIN to view your current balance.",
            [("pin", "4-digit PIN", "*")],
            "Show balance",
            submit,
        )

    def show_deposit_form(self) -> None:
        if self.customer is None:
            return
        customer_id = self.customer["Id"]

        def submit(values: dict[str, str]) -> None:
            new_balance = deposit(customer_id, _read_integer(values["amount"], "Amount"))
            self._complete_action(f"Deposit successful. New balance: {new_balance:,}.")

        self._show_form(
            "Deposit money",
            "Add funds to your account.",
            [("amount", "Amount", None)],
            "Confirm deposit",
            submit,
        )

    def show_withdraw_form(self) -> None:
        if self.customer is None:
            return
        customer_id = self.customer["Id"]

        def submit(values: dict[str, str]) -> None:
            new_balance = withdraw(
                customer_id, _read_integer(values["amount"], "Amount"), values["pin"]
            )
            self._complete_action(f"Withdrawal successful. New balance: {new_balance:,}.")

        self._show_form(
            "Withdraw money",
            "Enter an amount and verify your PIN.",
            [("amount", "Amount", None), ("pin", "4-digit PIN", "*")],
            "Confirm withdrawal",
            submit,
        )

    def show_transfer_form(self) -> None:
        if self.customer is None:
            return
        customer_id = self.customer["Id"]

        def submit(values: dict[str, str]) -> None:
            result = transfer_money(
                customer_id,
                _read_integer(values["account"], "Recipient account number"),
                _read_integer(values["amount"], "Amount"),
                values["pin"],
            )
            self._complete_action(result)

        self._show_form(
            "Transfer money",
            "Send funds to another Northstar account.",
            [
                ("account", "Recipient account number", None),
                ("amount", "Amount", None),
                ("pin", "4-digit PIN", "*"),
            ],
            "Confirm transfer",
            submit,
        )

    def show_pin_form(self) -> None:
        if self.customer is None:
            return
        customer_id = self.customer["Id"]
        if self.customer["Pin"] is None:
            def submit(values: dict[str, str]) -> None:
                create_pin(customer_id, values["new_pin"])
                self._complete_action("Your PIN has been created.")

            self._show_form(
                "Create a PIN",
                "Set a 4-digit PIN to authorize withdrawals and transfers.",
                [("new_pin", "New 4-digit PIN", "*")],
                "Create PIN",
                submit,
            )
        else:
            def submit(values: dict[str, str]) -> None:
                update_pin(customer_id, values["current_pin"], values["new_pin"])
                self._complete_action("Your PIN has been updated.")

            self._show_form(
                "Update your PIN",
                "Verify your current PIN, then choose a new one.",
                [
                    ("current_pin", "Current PIN", "*"),
                    ("new_pin", "New 4-digit PIN", "*"),
                ],
                "Update PIN",
                submit,
            )

    def show_history(self) -> None:
        if self.customer is None:
            return
        panel = self._panel("Transactions", "Your 10 most recent account transactions.")
        columns = ("date", "type", "amount", "from", "to")
        table = ttk.Treeview(panel, columns=columns, show="headings", style="Bank.Treeview")
        headings = {
            "date": ("Date", 180),
            "type": ("Type", 120),
            "amount": ("Amount", 100),
            "from": ("From account", 150),
            "to": ("To account", 150),
        }
        for key, (label, width) in headings.items():
            table.heading(key, text=label)
            table.column(key, width=width, anchor="w")
        table.pack(fill="both", expand=True, pady=(12, 0))
        rows = get_transaction_history(self.customer["Account"], limit=10)
        for row in rows:
            table.insert(
                "",
                "end",
                values=(
                    row["DateAndTime"],
                    row["Type"],
                    f"{row['AmountTransferred']:,}",
                    row["FromAccount"] if row["FromAccount"] is not None else "-",
                    row["ToAccount"] if row["ToAccount"] is not None else "-",
                ),
            )
        if not rows:
            tk.Label(
                panel,
                text="No transactions yet.",
                bg=SURFACE,
                fg=MUTED,
                font=("Segoe UI", 10),
            ).pack(anchor="w", pady=(12, 0))

    def show_admin_dashboard(self) -> None:
        summary = get_admin_summary()
        self._clear()
        outer = tk.Frame(self.root, bg=BACKGROUND, padx=34, pady=28)
        outer.pack(fill="both", expand=True)
        topbar = tk.Frame(outer, bg=BACKGROUND)
        topbar.pack(fill="x", pady=(0, 22))
        tk.Label(
            topbar,
            text="Admin overview",
            bg=BACKGROUND,
            fg=INK,
            font=("Segoe UI", 22, "bold"),
        ).pack(side="left")
        self._button(topbar, "Sign out", self.show_welcome).pack(side="right")
        panel = tk.Frame(
            outer,
            bg=SURFACE,
            padx=28,
            pady=26,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        panel.pack(fill="both", expand=True)
        tk.Label(
            panel,
            text=f"Customers   {summary['total_customers']:,}",
            bg=PALE_GREEN,
            fg=GREEN_DARK,
            padx=16,
            pady=12,
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")
        tk.Label(
            panel,
            text=f"Total balance   {summary['total_balance']:,}",
            bg=PALE_GREEN,
            fg=GREEN_DARK,
            padx=16,
            pady=12,
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", pady=(8, 18))
        tk.Label(
            panel,
            text="Recent transactions",
            bg=SURFACE,
            fg=INK,
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))
        columns = ("date", "type", "amount", "from", "to")
        table = ttk.Treeview(panel, columns=columns, show="headings", style="Bank.Treeview")
        for key, label, width in (
            ("date", "Date", 180),
            ("type", "Type", 120),
            ("amount", "Amount", 100),
            ("from", "From account", 150),
            ("to", "To account", 150),
        ):
            table.heading(key, text=label)
            table.column(key, width=width, anchor="w")
        table.pack(fill="both", expand=True)
        for row in summary["recent_transactions"]:
            table.insert(
                "",
                "end",
                values=(
                    row["DateAndTime"],
                    row["Type"],
                    f"{row['AmountTransferred']:,}",
                    row["FromAccount"] if row["FromAccount"] is not None else "-",
                    row["ToAccount"] if row["ToAccount"] is not None else "-",
                ),
            )


def run_tkinter_app() -> None:
    root = tk.Tk()
    BankTkApp(root)
    root.mainloop()
