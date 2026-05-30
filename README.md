# Digital Wallet System

A peer-to-peer digital wallet web application simulating core payment flows including deposits, withdrawals, transfers, and real-time fraud detection. Built with Python and Streamlit.

## Overview

Users can register accounts, authenticate with a PIN, send money to other users, and view their full transaction history. The system automatically flags suspicious transactions based on amount thresholds and transaction velocity.

## Features

- User registration and PIN-based authentication with SHA-256 hashing
- Deposit, withdraw, and peer-to-peer transfer between accounts
- Real-time fraud detection flagging large transactions over $1,000 and velocity alerts
- Full transaction history with fraud indicators per transaction
- Persistent storage using SQLite with a relational schema
- Clean web interface built with Streamlit

## Technologies

Python, Streamlit, SQLite, hashlib

## How to Run

Install dependencies with `pip install streamlit` then run `streamlit run wallet_app.py` and open `http://localhost:8501` in your browser. Register two accounts and transfer money between them to test the fraud detection system.

---
Built by Mahmoud Abdelwahab Shaaban — Communications and Information Engineering, Zewail City of Science and Technology
