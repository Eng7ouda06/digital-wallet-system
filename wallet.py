# ============================================================
#  Digital Wallet Simulation System
#  Mahmoud Abdelwahab Shaaban — Resume Project #3
# ============================================================
#
#  SETUP (run once in your terminal):
#  py -m pip install rich
#
#  HOW TO RUN:
#  py wallet.py
# ============================================================

import sqlite3
import hashlib
import random
import string
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

# ── Database Setup ────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("wallet.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            pin_hash    TEXT NOT NULL,
            balance     REAL DEFAULT 0.0,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sender      TEXT,
            receiver    TEXT,
            amount      REAL NOT NULL,
            type        TEXT NOT NULL,
            note        TEXT,
            timestamp   TEXT DEFAULT CURRENT_TIMESTAMP,
            flagged     INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()

# ── Helpers ───────────────────────────────────────────────────
def hash_pin(pin):
    return hashlib.sha256(pin.encode()).hexdigest()

def get_user(username):
    conn = sqlite3.connect("wallet.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return user

def update_balance(username, new_balance):
    conn = sqlite3.connect("wallet.db")
    c = conn.cursor()
    c.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, username))
    conn.commit()
    conn.close()

def log_transaction(sender, receiver, amount, tx_type, note="", flagged=0):
    conn = sqlite3.connect("wallet.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO transactions (sender, receiver, amount, type, note, flagged)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (sender, receiver, amount, tx_type, note, flagged))
    conn.commit()
    conn.close()

def fraud_check(username, amount):
    """Flag if single transaction > $1000 or 3+ transactions in last minute."""
    conn = sqlite3.connect("wallet.db")
    c = conn.cursor()

    # Velocity check — more than 3 transactions in last 60 seconds
    c.execute("""
        SELECT COUNT(*) FROM transactions
        WHERE sender = ? AND timestamp >= datetime('now', '-1 minute')
    """, (username,))
    recent_count = c.fetchone()[0]
    conn.close()

    if amount > 1000:
        return True, "⚠️  Large transaction detected (> $1,000)"
    if recent_count >= 3:
        return True, "⚠️  Velocity alert: too many transactions in short period"
    return False, ""

# ── Features ──────────────────────────────────────────────────
def register():
    console.print("\n[bold cyan]── Create New Account ──[/bold cyan]")
    username = console.input("[white]Choose a username: [/white]").strip()

    if get_user(username):
        console.print("[red]Username already taken.[/red]")
        return

    pin = console.input("[white]Set a 4-digit PIN: [/white]").strip()
    if not pin.isdigit() or len(pin) != 4:
        console.print("[red]PIN must be exactly 4 digits.[/red]")
        return

    initial = console.input("[white]Initial deposit ($): [/white]").strip()
    try:
        initial = float(initial)
        if initial < 0:
            raise ValueError
    except ValueError:
        console.print("[red]Invalid amount.[/red]")
        return

    conn = sqlite3.connect("wallet.db")
    c = conn.cursor()
    c.execute("INSERT INTO users (username, pin_hash, balance) VALUES (?, ?, ?)",
              (username, hash_pin(pin), initial))
    conn.commit()
    conn.close()

    log_transaction(None, username, initial, "DEPOSIT", "Initial deposit")
    console.print(f"\n[green]✅ Account created! Welcome, {username}. Balance: ${initial:.2f}[/green]")


def login():
    console.print("\n[bold cyan]── Login ──[/bold cyan]")
    username = console.input("[white]Username: [/white]").strip()
    pin      = console.input("[white]PIN: [/white]").strip()

    user = get_user(username)
    if not user or user[2] != hash_pin(pin):
        console.print("[red]Invalid username or PIN.[/red]")
        return None

    console.print(f"\n[green]✅ Welcome back, {username}![/green]")
    return username


def deposit(username):
    console.print("\n[bold cyan]── Deposit ──[/bold cyan]")
    try:
        amount = float(console.input("[white]Amount to deposit ($): [/white]").strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        console.print("[red]Invalid amount.[/red]")
        return

    user = get_user(username)
    new_balance = user[3] + amount
    update_balance(username, new_balance)
    log_transaction(None, username, amount, "DEPOSIT")
    console.print(f"[green]✅ Deposited ${amount:.2f}. New balance: ${new_balance:.2f}[/green]")


def withdraw(username):
    console.print("\n[bold cyan]── Withdraw ──[/bold cyan]")
    try:
        amount = float(console.input("[white]Amount to withdraw ($): [/white]").strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        console.print("[red]Invalid amount.[/red]")
        return

    user = get_user(username)
    if amount > user[3]:
        console.print(f"[red]Insufficient funds. Balance: ${user[3]:.2f}[/red]")
        return

    flagged, reason = fraud_check(username, amount)
    if flagged:
        console.print(f"[yellow]{reason}[/yellow]")
        confirm = console.input("[white]Proceed anyway? (yes/no): [/white]").strip().lower()
        if confirm != "yes":
            console.print("[red]Transaction cancelled.[/red]")
            return

    new_balance = user[3] - amount
    update_balance(username, new_balance)
    log_transaction(username, None, amount, "WITHDRAW", flagged=int(flagged))
    console.print(f"[green]✅ Withdrew ${amount:.2f}. New balance: ${new_balance:.2f}[/green]")


def transfer(username):
    console.print("\n[bold cyan]── Transfer ──[/bold cyan]")
    recipient = console.input("[white]Recipient username: [/white]").strip()

    if recipient == username:
        console.print("[red]Cannot transfer to yourself.[/red]")
        return

    if not get_user(recipient):
        console.print("[red]Recipient not found.[/red]")
        return

    try:
        amount = float(console.input("[white]Amount to transfer ($): [/white]").strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        console.print("[red]Invalid amount.[/red]")
        return

    note = console.input("[white]Note (optional): [/white]").strip()

    user = get_user(username)
    if amount > user[3]:
        console.print(f"[red]Insufficient funds. Balance: ${user[3]:.2f}[/red]")
        return

    flagged, reason = fraud_check(username, amount)
    if flagged:
        console.print(f"[yellow]{reason}[/yellow]")
        confirm = console.input("[white]Proceed anyway? (yes/no): [/white]").strip().lower()
        if confirm != "yes":
            console.print("[red]Transaction cancelled.[/red]")
            return

    # Debit sender, credit receiver
    recipient_user = get_user(recipient)
    update_balance(username,  user[3] - amount)
    update_balance(recipient, recipient_user[3] + amount)
    log_transaction(username, recipient, amount, "TRANSFER", note, flagged=int(flagged))

    console.print(f"[green]✅ Sent ${amount:.2f} to {recipient}. New balance: ${user[3]-amount:.2f}[/green]")


def view_history(username):
    console.print("\n[bold cyan]── Transaction History ──[/bold cyan]")
    conn = sqlite3.connect("wallet.db")
    c = conn.cursor()
    c.execute("""
        SELECT type, sender, receiver, amount, note, timestamp, flagged
        FROM transactions
        WHERE sender = ? OR receiver = ?
        ORDER BY timestamp DESC LIMIT 15
    """, (username, username))
    rows = c.fetchall()
    conn.close()

    if not rows:
        console.print("[yellow]No transactions yet.[/yellow]")
        return

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Type",      style="cyan",  width=10)
    table.add_column("From",      style="white", width=12)
    table.add_column("To",        style="white", width=12)
    table.add_column("Amount",    style="green", width=10)
    table.add_column("Note",      style="white", width=18)
    table.add_column("Time",      style="dim",   width=20)
    table.add_column("Flag",      style="yellow",width=5)

    for row in rows:
        tx_type, sender, receiver, amount, note, timestamp, flagged = row
        table.add_row(
            tx_type,
            sender or "—",
            receiver or "—",
            f"${amount:.2f}",
            note or "—",
            timestamp,
            "⚠️" if flagged else "✅"
        )

    console.print(table)


def check_balance(username):
    user = get_user(username)
    console.print(Panel(
        f"[bold green]${user[3]:,.2f}[/bold green]",
        title=f"[cyan]{username}'s Balance[/cyan]",
        expand=False
    ))


# ── Main App Loop ─────────────────────────────────────────────
def main():
    init_db()
    console.print(Panel.fit(
        "[bold cyan]💳 Digital Wallet System[/bold cyan]\n"
        "[dim]Mahmoud Abdelwahab Shaaban — Resume Project #3[/dim]",
        box=box.DOUBLE
    ))

    current_user = None

    while True:
        if not current_user:
            console.print("\n[bold]Main Menu[/bold]")
            console.print("  [cyan]1[/cyan] Register")
            console.print("  [cyan]2[/cyan] Login")
            console.print("  [cyan]3[/cyan] Exit")
            choice = console.input("\n[white]Choose: [/white]").strip()

            if choice == "1":
                register()
            elif choice == "2":
                current_user = login()
            elif choice == "3":
                console.print("[dim]Goodbye![/dim]")
                break

        else:
            user = get_user(current_user)
            console.print(f"\n[bold]Wallet Menu[/bold] [dim]— {current_user} | Balance: ${user[3]:,.2f}[/dim]")
            console.print("  [cyan]1[/cyan] Check Balance")
            console.print("  [cyan]2[/cyan] Deposit")
            console.print("  [cyan]3[/cyan] Withdraw")
            console.print("  [cyan]4[/cyan] Transfer")
            console.print("  [cyan]5[/cyan] Transaction History")
            console.print("  [cyan]6[/cyan] Logout")
            choice = console.input("\n[white]Choose: [/white]").strip()

            if choice == "1":
                check_balance(current_user)
            elif choice == "2":
                deposit(current_user)
            elif choice == "3":
                withdraw(current_user)
            elif choice == "4":
                transfer(current_user)
            elif choice == "5":
                view_history(current_user)
            elif choice == "6":
                console.print(f"[dim]Logged out. Goodbye, {current_user}![/dim]")
                current_user = None

if __name__ == "__main__":
    main()
