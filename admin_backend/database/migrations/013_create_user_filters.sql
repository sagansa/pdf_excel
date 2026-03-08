-- Create user_filters table to persist UI filter states
CREATE TABLE IF NOT EXISTS user_filters (
    view_name VARCHAR(50) PRIMARY KEY,
    filters JSON NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
