-- Add PPh 4(2) payment reference number to rental contracts
ALTER TABLE rental_contracts ADD COLUMN pph42_payment_ref VARCHAR(100) DEFAULT NULL;
