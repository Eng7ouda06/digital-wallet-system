# ============================================================
#  Digital Wallet Web App
#  Mahmoud Abdelwahab Shaaban — Resume Project #3
# ============================================================
#
#  HOW TO RUN:
#  py -m streamlit run wallet_app.py
# ============================================================

import streamlit as st
import sqlite3
import hashlib
from datetime import datetime

# ── Page Config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Digital Wallet",
    page_icon="💳",
    layout="centered"
)

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
.balance-card {
    background: linear-gradient(135deg, #1e3a5f, #2563EB);
    border-radius: 16px;
    padding: 30px;
    text-align: center;
    color: white;
    margin-bottom: 20px;
}
.balance-label { font-size: 14px; opacity: 0.8; margin-bottom: 4px; }
.balance-amount { font-size: 48px; font-weight: 700; }
.balance-user { font-size: 14px; opacity: 0.7; margin-top: 6px; }
.tx-row { padding: 10px 0; border-bottom: 1px solid #eee; }
.fraud-badge { background:#FEF3C7; color:#92400E; padding:2px 8px; border-radius:4px; font-size:12px; }
.ok-badge { background:#D1FAE5; color:#065F46; padding:2px 8px; border-radius:4px; font-size:12px; }
</style>
""", unsafe_allow_html=True)

# ── Database ──────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("wallet.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        pin_hash TEXT NOT NULL,
        balance REAL DEFAULT 0.0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT, receiver TEXT,
        amount REAL, type TEXT, note TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        flagged INTEGER DEFAULT 0
    )""")
    conn.commit()
    return conn

conn = init_db()

def hash_pin(pin):
    return hashlib.sha256(pin.encode()).hexdigest()

def get_user(username):
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    return c.fetchone()

def update_balance(username, amount):
    c = conn.cursor()
    c.execute("UPDATE users SET balance=? WHERE username=?", (amount, username))
    conn.commit()

def log_tx(sender, receiver, amount, tx_type, note="", flagged=0):
    c = conn.cursor()
    c.execute("INSERT INTO transactions (sender,receiver,amount,type,note,flagged) VALUES (?,?,?,?,?,?)",
              (sender, receiver, amount, tx_type, note, flagged))
    conn.commit()

def fraud_check(username, amount):
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM transactions WHERE sender=? AND timestamp>=datetime('now','-1 minute')", (username,))
    count = c.fetchone()[0]
    if amount > 1000:
        return True, "Large transaction (> $1,000)"
    if count >= 3:
        return True, "Velocity alert: too many transactions"
    return False, ""

def get_history(username):
    c = conn.cursor()
    c.execute("""SELECT type,sender,receiver,amount,note,timestamp,flagged
                 FROM transactions WHERE sender=? OR receiver=?
                 ORDER BY timestamp DESC LIMIT 20""", (username, username))
    return c.fetchall()

def all_users():
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    return [r[0] for r in c.fetchall()]

# ── Session State ─────────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "login"

# ── Auth Screen ───────────────────────────────────────────────
if not st.session_state.user:
    st.title("💳 Digital Wallet")
    st.markdown("A peer-to-peer payment simulation with fraud detection")
    st.markdown("---")

    tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            pin      = st.text_input("PIN", type="password", max_chars=4)
            submitted = st.form_submit_button("Login", use_container_width=True)
            if submitted:
                user = get_user(username)
                if user and user[2] == hash_pin(pin):
                    st.session_state.user = username
                    st.rerun()
                else:
                    st.error("Invalid username or PIN.")

    with tab2:
        with st.form("register_form"):
            new_user    = st.text_input("Choose a username")
            new_pin     = st.text_input("Set a 4-digit PIN", type="password", max_chars=4)
            initial_dep = st.number_input("Initial deposit ($)", min_value=0.0, value=100.0, step=10.0)
            submitted   = st.form_submit_button("Create Account", use_container_width=True)
            if submitted:
                if not new_pin.isdigit() or len(new_pin) != 4:
                    st.error("PIN must be exactly 4 digits.")
                elif get_user(new_user):
                    st.error("Username already taken.")
                else:
                    c = conn.cursor()
                    c.execute("INSERT INTO users (username,pin_hash,balance) VALUES (?,?,?)",
                              (new_user, hash_pin(new_pin), initial_dep))
                    conn.commit()
                    log_tx(None, new_user, initial_dep, "DEPOSIT", "Initial deposit")
                    st.success(f"Account created! You can now log in as {new_user}.")

# ── Main Wallet App ───────────────────────────────────────────
else:
    username = st.session_state.user
    user     = get_user(username)
    balance  = user[3]

    # ── Balance Card ──────────────────────────────────────────
    st.markdown(f"""
    <div class="balance-card">
        <div class="balance-label">Available Balance</div>
        <div class="balance-amount">${balance:,.2f}</div>
        <div class="balance-user">👤 {username}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Logout ────────────────────────────────────────────────
    if st.button("🚪 Logout", use_container_width=False):
        st.session_state.user = None
        st.rerun()

    st.markdown("---")

    # ── Action Tabs ───────────────────────────────────────────
    tab_dep, tab_with, tab_trans, tab_hist = st.tabs(["💰 Deposit", "🏧 Withdraw", "📤 Transfer", "📋 History"])

    # ── DEPOSIT ───────────────────────────────────────────────
    with tab_dep:
        st.subheader("Deposit Funds")
        with st.form("deposit_form"):
            amount = st.number_input("Amount ($)", min_value=1.0, value=50.0, step=10.0)
            note   = st.text_input("Note (optional)")
            if st.form_submit_button("Deposit", use_container_width=True):
                new_bal = balance + amount
                update_balance(username, new_bal)
                log_tx(None, username, amount, "DEPOSIT", note)
                st.success(f"✅ Deposited ${amount:.2f} — New balance: ${new_bal:.2f}")
                st.rerun()

    # ── WITHDRAW ──────────────────────────────────────────────
    with tab_with:
        st.subheader("Withdraw Funds")
        with st.form("withdraw_form"):
            amount = st.number_input("Amount ($)", min_value=1.0, value=50.0, step=10.0)
            note   = st.text_input("Note (optional)")
            submitted = st.form_submit_button("Withdraw", use_container_width=True)
            if submitted:
                if amount > balance:
                    st.error(f"Insufficient funds. Balance: ${balance:.2f}")
                else:
                    flagged, reason = fraud_check(username, amount)
                    if flagged:
                        st.warning(f"⚠️ Fraud alert: {reason}")
                    new_bal = balance - amount
                    update_balance(username, new_bal)
                    log_tx(username, None, amount, "WITHDRAW", note, int(flagged))
                    st.success(f"✅ Withdrew ${amount:.2f} — New balance: ${new_bal:.2f}")
                    st.rerun()

    # ── TRANSFER ──────────────────────────────────────────────
    with tab_trans:
        st.subheader("Send Money")
        users = [u for u in all_users() if u != username]

        if not users:
            st.info("No other users yet. Register another account to try transfers!")
        else:
            with st.form("transfer_form"):
                recipient = st.selectbox("Send to", users)
                amount    = st.number_input("Amount ($)", min_value=1.0, value=20.0, step=5.0)
                note      = st.text_input("Note (e.g. 'Lunch split')")
                submitted = st.form_submit_button("Send Money 💸", use_container_width=True)
                if submitted:
                    if amount > balance:
                        st.error(f"Insufficient funds. Balance: ${balance:.2f}")
                    else:
                        flagged, reason = fraud_check(username, amount)
                        rec_user = get_user(recipient)
                        update_balance(username,  balance - amount)
                        update_balance(recipient, rec_user[3] + amount)
                        log_tx(username, recipient, amount, "TRANSFER", note, int(flagged))
                        if flagged:
                            st.warning(f"⚠️ Fraud alert triggered: {reason}")
                        st.success(f"✅ Sent ${amount:.2f} to {recipient}!")
                        st.rerun()

    # ── HISTORY ───────────────────────────────────────────────
    with tab_hist:
        st.subheader("Transaction History")
        history = get_history(username)

        if not history:
            st.info("No transactions yet.")
        else:
            for tx in history:
                tx_type, sender, receiver, amount, note, timestamp, flagged = tx
                col1, col2, col3 = st.columns([2, 2, 1])

                # Direction indicator
                if tx_type == "DEPOSIT":
                    icon = "⬇️"
                    label = "Deposit"
                    color = "green"
                elif tx_type == "WITHDRAW":
                    icon = "⬆️"
                    label = "Withdrawal"
                    color = "red"
                else:
                    if sender == username:
                        icon = "📤"
                        label = f"To {receiver}"
                        color = "red"
                    else:
                        icon = f"📥"
                        label = f"From {sender}"
                        color = "green"

                with col1:
                    st.markdown(f"**{icon} {label}**")
                    st.caption(note or "—")
                with col2:
                    st.markdown(f":{color}[**${amount:.2f}**]")
                    st.caption(timestamp)
                with col3:
                    if flagged:
                        st.markdown('<span class="fraud-badge">⚠️ Flagged</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="ok-badge">✅ OK</span>', unsafe_allow_html=True)
                st.divider()
