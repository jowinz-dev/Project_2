from email.mime import text

from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)
DB_FILE = "database.db"

def init_db():
    """Creates the database tables if they do not exist and adds dummy items."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transaction_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_text TEXT NOT NULL,
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                stock_quantity INTEGER NOT NULL,
                price_per_unit REAL NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                phone_number TEXT,
                total_debt REAL DEFAULT 0.0
            )
        ''')
        
        # Seed initial dummy stock items if empty
        cursor.execute("SELECT COUNT(*) FROM inventory")
        if cursor.fetchone()[0] == 0:
            cursor.executemany('''
                INSERT INTO inventory (item_name, stock_quantity, price_per_unit)
                VALUES (?, ?, ?)
            ''', [
                ('Sugar (1kg)', 15, 5000),
                ('Cooking Oil (1L)', 4, 9000),
                ('Bar Soap', 2, 4500),
                ('Maize Flour (1kg)', 25, 3500)
            ])
        conn.commit()
def log_activity(text):
    """Inserts a historical event message into the database logs table."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO transaction_logs (activity_text) VALUES (?)", (text,))
        conn.commit()
        
@app.route('/')
def dashboard():
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        inventory = cursor.execute("SELECT * FROM inventory").fetchall()
        customers = cursor.execute("SELECT * FROM customers WHERE total_debt > 0").fetchall()
        all_customers = cursor.execute("SELECT * FROM customers").fetchall()

    logs = cursor.execute("SELECT * FROM transaction_logs ORDER BY date_created DESC LIMIT 10").fetchall()

    return render_template('index.html', inventory=inventory, customers=customers, all_customers=all_customers, logs=logs)

@app.route('/sell', methods=['POST'])
def sell_item():
    item_id = request.form.get('item_id')
    qty = int(request.form.get('quantity', 1))
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE inventory SET stock_quantity = MAX(0, stock_quantity - ?) WHERE id = ?", (qty, item_id))
        conn.commit()
    return redirect(url_for('dashboard'))

@app.route('/add-customer', methods=['POST'])
def add_customer():
    name = request.form.get('customer_name')
    phone = request.form.get('phone_number')
    
    if name:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO customers (customer_name, phone_number) VALUES (?, ?)", (name, phone))
            conn.commit()
    return redirect(url_for('dashboard'))

@app.route('/update-debt', methods=['POST'])
def update_debt():
    customer_id = request.form.get('customer_id')
    amount = float(request.form.get('amount', 0))
    action = request.form.get('action') # 'add' or 'pay'
    
    if action == 'pay':
        amount = -amount
        
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE customers SET total_debt = MAX(0.0, total_debt + ?) WHERE id = ?", (amount, customer_id))
        conn.commit()
    return redirect(url_for('dashboard'))


@app.route('/restock', methods=['POST'])
def restock_item():
    item_id = request.form.get('item_id')
    added_qty = int(request.form.get('quantity', 0))
    
    if added_qty > 0:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE inventory SET stock_quantity = stock_quantity + ? WHERE id = ?", (added_qty, item_id))
            conn.commit()
    return redirect(url_for('dashboard'))
@app.route('/add-item', methods=['POST'])
def add_new_item():
    name = request.form.get('item_name')
    qty = int(request.form.get('stock_quantity', 0))
    price = float(request.form.get('price_per_unit', 0))
    
    if name and qty >= 0 and price >= 0:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO inventory (item_name, stock_quantity, price_per_unit) VALUES (?, ?, ?)",
                (name, qty, price)
            )
            conn.commit()
        # Log the activity
        log_activity(f"Added brand new item to inventory: {name} (Initial Qty: {qty})")
        
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
import os
port = int(os.environ.get("PORT", 5000))
    app.run(
        host='0.0.0.0', 
        port=port, 
    )
