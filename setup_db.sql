-- ==========================================
-- STEP 1: MySQL Schema Setup
-- Database: fraud_db
-- User: fraud_user
-- Tables: accounts, transactions, alerts
-- ==========================================

-- 1. Create the database
-- Why: We need a dedicated namespace/database to isolate our application data.
CREATE DATABASE IF NOT EXISTS fraud_db;

-- 2. Create the application user
-- Why: Connecting as 'root' in applications is a security risk. Creating a separate
-- user 'fraud_user' limits access and enforces the principle of least privilege.
CREATE USER IF NOT EXISTS 'fraud_user'@'localhost' IDENTIFIED BY 'fraud_secure_pwd_123';

-- 3. Grant privileges
-- Why: The application user needs permissions to create, read, update, and delete
-- records only inside our newly created database 'fraud_db'.
GRANT ALL PRIVILEGES ON fraud_db.* TO 'fraud_user'@'localhost';

-- Why: Flush privileges forces MySQL to reload grant tables, making user changes active immediately.
FLUSH PRIVILEGES;

-- Use the database context for table creation
USE fraud_db;

-- 4. Create the 'accounts' table
-- Why: Serves as the master registry for customer bank accounts.
-- - account_id: Primary key, auto-incremented to uniquely identify each account.
-- - balance: DECIMAL(15, 2) is used instead of FLOAT/DOUBLE to prevent floating-point rounding errors on currency.
CREATE TABLE IF NOT EXISTS accounts (
    account_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    account_type VARCHAR(50) NOT NULL, -- e.g., Savings, Checking, Money Market
    branch VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    opened_date DATE NOT NULL,
    balance DECIMAL(15, 2) NOT NULL
);

-- 5. Create the 'transactions' table
-- Why: Stores every individual banking activity.
-- - txn_id: Primary key, auto-incremented.
-- - account_id: Foreign key mapping back to the 'accounts' table to maintain referential integrity.
-- - is_flagged: Boolean indicator (stored as TINYINT(1) in MySQL) to flag suspicious activity.
CREATE TABLE IF NOT EXISTS transactions (
    txn_id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    txn_date DATETIME NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    txn_type VARCHAR(50) NOT NULL, -- e.g., Withdrawal, Deposit, Transfer, POS Purchase
    merchant VARCHAR(150) DEFAULT NULL,
    city VARCHAR(100) NOT NULL,
    is_flagged TINYINT(1) DEFAULT 0,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
);

-- 6. Create the 'alerts' table
-- Why: Documents details about flagged transactions, indicating which rule was triggered and when.
-- - alert_id: Primary key, auto-incremented.
-- - txn_id: Foreign key mapping to 'transactions' to link the alert back to the transaction.
CREATE TABLE IF NOT EXISTS alerts (
    alert_id INT AUTO_INCREMENT PRIMARY KEY,
    txn_id INT NOT NULL,
    rule_triggered VARCHAR(255) NOT NULL, -- e.g., 'Out of State Spend', 'High Deviation Amount'
    flagged_at DATETIME NOT NULL,
    FOREIGN KEY (txn_id) REFERENCES transactions(txn_id) ON DELETE CASCADE
);
