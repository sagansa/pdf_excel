ALTER TABLE initial_capital_settings
ADD COLUMN previous_retained_earnings_amount DECIMAL(15,2) NOT NULL DEFAULT 0.00
AFTER amount;
