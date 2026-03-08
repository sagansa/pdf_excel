-- Migration 000: Create base transactions table
CREATE TABLE IF NOT EXISTS transactions (
  id char(36) NOT NULL,
  txn_date date DEFAULT NULL,
  description text,
  amount decimal(15,2) DEFAULT NULL,
  db_cr char(2) DEFAULT NULL,
  bank_code varchar(50) DEFAULT NULL,
  source_file varchar(255) DEFAULT NULL,
  file_hash varchar(32) DEFAULT NULL,
  mark_id char(36) DEFAULT NULL,
  company_id char(36) DEFAULT NULL,
  created_at datetime DEFAULT CURRENT_TIMESTAMP,
  updated_at datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  rental_contract_id char(36) DEFAULT NULL,
  PRIMARY KEY (id),
  KEY idx_file_hash (file_hash),
  KEY idx_transactions_company_id (company_id),
  KEY idx_transactions_contract (rental_contract_id)
);
