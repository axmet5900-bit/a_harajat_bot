import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('wallet.db', check_same_thread=False)
        self.c = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        """Barcha jadvallarni yaratish"""
        
        # Foydalanuvchilar
        self.c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language TEXT DEFAULT 'uz',
            currency TEXT DEFAULT 'UZS',
            monthly_income REAL DEFAULT 0,
            daily_budget REAL DEFAULT 0,
            pin_code TEXT,
            notification_time TEXT DEFAULT '09:00',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Xarajatlar
        self.c.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            category TEXT,
            type TEXT CHECK(type IN ('income', 'expense')),
            description TEXT,
            date TEXT,
            receipt_image TEXT,
            is_recurring BOOLEAN DEFAULT 0,
            recurring_interval TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Kategoriyalar
        self.c.execute('''CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            emoji TEXT DEFAULT '📌',
            budget REAL DEFAULT 0,
            color TEXT DEFAULT '#808080',
            is_default BOOLEAN DEFAULT 0,
            UNIQUE(user_id, name)
        )''')
        
        # Qarzlar
        self.c.execute('''CREATE TABLE IF NOT EXISTS debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            person TEXT,
            amount REAL,
            type TEXT CHECK(type IN ('debt', 'loan')),
            status TEXT DEFAULT 'active',
            due_date TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Bank kartalari
        self.c.execute('''CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            card_number TEXT,
            card_name TEXT,
            bank_name TEXT,
            balance REAL DEFAULT 0,
            currency TEXT DEFAULT 'UZS',
            is_active BOOLEAN DEFAULT 1
        )''')
        
        # Valyuta kurslari
        self.c.execute('''CREATE TABLE IF NOT EXISTS currency_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            currency TEXT,
            rate REAL,
            date TEXT
        )''')
        
        # Eslatmalar
        self.c.execute('''CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            amount REAL,
            due_date TEXT,
            is_paid BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Zaxira nusxalar
        self.c.execute('''CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            backup_date TEXT,
            file_path TEXT
        )''')
        
        self.conn.commit()
        
        # Default kategoriyalar
        self.add_default_categories()
    
    def add_default_categories(self):
        """Standart kategoriyalarni qo'shish"""
        default_cats = [
            ('Oziq-ovqat', '🍔', '#FF6B6B'),
            ('Transport', '🚗', '#4ECDC4'),
            ('Uy-joy', '🏠', '#45B7D1'),
            ('Telefon', '📱', '#96CEB4'),
            ('Kiyim', '👕', '#FFEAA7'),
            ('Sogʻliq', '🏥', '#D4A5A5'),
            ('Taʼlim', '🎓', '#9B59B6'),
            ('Koʻngilochar', '🎮', '#F1C40F'),
            ('Daromad', '💰', '#2ECC71'),
            ('Boshqa', '📌', '#95A5A6')
        ]
        
        for name, emoji, color in default_cats:
            self.c.execute('''INSERT OR IGNORE INTO categories (user_id, name, emoji, color, is_default) 
                            VALUES (0, ?, ?, ?, 1)''', (name, emoji, color))
        self.conn.commit()
    
    # ========== USER METHODS ==========
    
    def add_user(self, user_id, username, first_name, last_name=None):
        self.c.execute('''INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, last_active)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)''',
                        (user_id, username, first_name, last_name))
        self.conn.commit()
        
        # User uchun kategoriyalarni qo'shish
        self.c.execute('''INSERT INTO categories (user_id, name, emoji, color)
                        SELECT ?, name, emoji, color FROM categories WHERE user_id=0''',
                        (user_id,))
        self.conn.commit()
    
    def get_user(self, user_id):
        self.c.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
        return self.c.fetchone()
    
    def update_user_settings(self, user_id, **kwargs):
        allowed = ['language', 'currency', 'monthly_income', 'daily_budget', 
                   'pin_code', 'notification_time']
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if updates:
            set_clause = ', '.join(f"{k}=?" for k in updates.keys())
            values = list(updates.values()) + [user_id]
            self.c.execute(f"UPDATE users SET {set_clause} WHERE user_id=?", values)
            self.conn.commit()
    
    # ========== TRANSACTION METHODS ==========
    
    def add_transaction(self, user_id, amount, category, type, description=''):
        date_now = datetime.now().strftime('%Y-%m-%d')
        self.c.execute('''INSERT INTO transactions (user_id, amount, category, type, description, date)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                        (user_id, amount, category, type, description, date_now))
        self.conn.commit()
        
        # Kategoriya ishlatilishini yangilash
        self.c.execute('''UPDATE categories SET usage_count = COALESCE(usage_count, 0) + 1 
                        WHERE user_id=? AND name=?''', (user_id, category))
        self.conn.commit()
        
        # Byudjetni tekshirish
        self.check_budget(user_id, category, amount)
        
        return self.c.lastrowid
    
    def get_transactions(self, user_id, days=30):
        date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        self.c.execute('''SELECT * FROM transactions 
                        WHERE user_id=? AND date>=? 
                        ORDER BY date DESC, created_at DESC''',
                        (user_id, date_from))
        return self.c.fetchall()
    
    def get_transactions_by_category(self, user_id, period='month'):
        if period == 'day':
            query = '''SELECT category, SUM(amount) as total 
                      FROM transactions WHERE user_id=? AND type='expense' 
                      AND date=date('now') GROUP BY category'''
        elif period == 'week':
            query = '''SELECT category, SUM(amount) as total 
                      FROM transactions WHERE user_id=? AND type='expense' 
                      AND date>=date('now', '-7 days') GROUP BY category'''
        else:
            query = '''SELECT category, SUM(amount) as total 
                      FROM transactions WHERE user_id=? AND type='expense' 
                      AND date>=date('now', 'start of month') GROUP BY category'''
        
        self.c.execute(query, (user_id,))
        return dict(self.c.fetchall())
    
    # ========== CATEGORY METHODS ==========
    
    def get_categories(self, user_id):
        self.c.execute('''SELECT * FROM categories WHERE user_id=? 
                        ORDER BY usage_count DESC, name''', (user_id,))
        return self.c.fetchall()
    
    def add_category(self, user_id, name, emoji='📌', color='#808080'):
        self.c.execute('''INSERT OR IGNORE INTO categories (user_id, name, emoji, color)
                        VALUES (?, ?, ?, ?)''', (user_id, name, emoji, color))
        self.conn.commit()
    
    def set_category_budget(self, user_id, category, amount):
        self.c.execute('''UPDATE categories SET budget=? 
                        WHERE user_id=? AND name=?''', (amount, user_id, category))
        self.conn.commit()
    
    def check_budget(self, user_id, category, amount):
        self.c.execute('''SELECT budget FROM categories 
                        WHERE user_id=? AND name=?''', (user_id, category))
        result = self.c.fetchone()
        if result and result[0] > 0:
            budget = result[0]
            
            # Shu oylik xarajat
            self.c.execute('''SELECT SUM(amount) FROM transactions 
                            WHERE user_id=? AND category=? AND type='expense' 
                            AND date>=date('now', 'start of month')''',
                            (user_id, category))
            spent = self.c.fetchone()[0] or 0
            
            if spent + amount > budget:
                return True, budget, spent
        return False, 0, 0
    
    # ========== DEBT METHODS ==========
    
    def add_debt(self, user_id, person, amount, type='debt', due_date=None):
        self.c.execute('''INSERT INTO debts (user_id, person, amount, type, due_date)
                        VALUES (?, ?, ?, ?, ?)''',
                        (user_id, person, amount, type, due_date))
        self.conn.commit()
        return self.c.lastrowid
    
    def get_debts(self, user_id, status='active'):
        self.c.execute('''SELECT * FROM debts WHERE user_id=? AND status=?
                        ORDER BY due_date, created_at''', (user_id, status))
        return self.c.fetchall()
    
    def pay_debt(self, debt_id):
        self.c.execute('''UPDATE debts SET status='paid' WHERE id=?''', (debt_id,))
        self.conn.commit()
        return self.c.rowcount > 0
    
    # ========== CARD METHODS ==========
    
    def add_card(self, user_id, card_number, card_name, bank_name, balance=0):
        self.c.execute('''INSERT INTO cards (user_id, card_number, card_name, bank_name, balance)
                        VALUES (?, ?, ?, ?, ?)''',
                        (user_id, card_number, card_name, bank_name, balance))
        self.conn.commit()
    
    def get_cards(self, user_id):
        self.c.execute('SELECT * FROM cards WHERE user_id=? AND is_active=1', (user_id,))
        return self.c.fetchall()
    
    def update_card_balance(self, card_id, amount):
        self.c.execute('''UPDATE cards SET balance=balance+? WHERE id=?''', (amount, card_id))
        self.conn.commit()
    
    # ========== REMINDER METHODS ==========
    
    def add_reminder(self, user_id, title, amount, due_date):
        self.c.execute('''INSERT INTO reminders (user_id, title, amount, due_date)
                        VALUES (?, ?, ?, ?)''', (user_id, title, amount, due_date))
        self.conn.commit()
    
    def get_reminders(self, user_id):
        self.c.execute('''SELECT * FROM reminders 
                        WHERE user_id=? AND is_paid=0 
                        ORDER BY due_date''', (user_id,))
        return self.c.fetchall()
    
    def check_reminders(self):
        today = datetime.now().strftime('%Y-%m-%d')
        self.c.execute('''SELECT * FROM reminders 
                        WHERE due_date=? AND is_paid=0''', (today,))
        return self.c.fetchall()
    
    # ========== RECURRING TRANSACTIONS ==========
    
    def detect_recurring(self, user_id):
        """Takrorlanuvchi to'lovlarni aniqlash"""
        self.c.execute('''SELECT category, AVG(amount) as avg_amount, COUNT(*) as count
                        FROM transactions WHERE user_id=? AND type='expense'
                        GROUP BY category HAVING count>=3''', (user_id,))
        return self.c.fetchall()
    
    # ========== STATISTICS ==========
    
    def get_monthly_report(self, user_id):
        year_month = datetime.now().strftime('%Y-%m')
        
        # Daromad
        self.c.execute('''SELECT SUM(amount) FROM transactions 
                        WHERE user_id=? AND type='income' 
                        AND strftime('%Y-%m', date)=?''', (user_id, year_month))
        income = self.c.fetchone()[0] or 0
        
        # Xarajat
        self.c.execute('''SELECT SUM(amount) FROM transactions 
                        WHERE user_id=? AND type='expense' 
                        AND strftime('%Y-%m', date)=?''', (user_id, year_month))
        expense = self.c.fetchone()[0] or 0
        
        # Kategoriyalar
        self.c.execute('''SELECT category, SUM(amount) as total 
                        FROM transactions WHERE user_id=? AND type='expense' 
                        AND strftime('%Y-%m', date)=? 
                        GROUP BY category ORDER BY total DESC''', (user_id, year_month))
        categories = self.c.fetchall()
        
        return {
            'income': income,
            'expense': expense,
            'balance': income - expense,
            'categories': categories
        }
    
    def get_top_categories(self, user_id, limit=5):
        self.c.execute('''SELECT category, SUM(amount) as total, COUNT(*) as count
                        FROM transactions WHERE user_id=? AND type='expense'
                        GROUP BY category ORDER BY total DESC LIMIT ?''',
                        (user_id, limit))
        return self.c.fetchall()
    
    def get_daily_trend(self, user_id, days=7):
        date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        self.c.execute('''SELECT date, SUM(amount) as total 
                        FROM transactions WHERE user_id=? AND type='expense'
                        AND date>=? GROUP BY date ORDER BY date''',
                        (user_id, date_from))
        return self.c.fetchall()
    
    # ========== BACKUP ==========
    
    def create_backup(self, user_id):
        """Foydalanuvchi ma'lumotlarini zaxiralash"""
        backup = {
            'user': self.get_user(user_id),
            'transactions': self.get_transactions(user_id, 3650),
            'debts': self.get_debts(user_id),
            'cards': self.get_cards(user_id),
            'categories': self.get_categories(user_id)
        }
        
        backup_date = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backup_{user_id}_{backup_date}.json"
        
        with open(filename, 'w') as f:
            json.dump(backup, f, default=str)
        
        self.c.execute('''INSERT INTO backups (user_id, backup_date, file_path)
                        VALUES (?, ?, ?)''', (user_id, backup_date, filename))
        self.conn.commit()
        
        return filename
    
    def restore_backup(self, backup_id):
        self.c.execute('SELECT * FROM backups WHERE id=?', (backup_id,))
        backup = self.c.fetchone()
        if backup:
            with open(backup[3], 'r') as f:
                data = json.load(f)
            return data
        return None
    
    # ========== CLOSE ==========
    
    def close(self):
        self.conn.close()

db = Database()
