from flask import Blueprint, request, jsonify, send_file, make_response
from sqlalchemy import text
from datetime import datetime
import io
import pandas as pd
from backend.db.session import get_db_engine

general_ledger_bp = Blueprint('general_ledger', __name__)

@general_ledger_bp.route('/api/reports/general-ledger', methods=['GET'])
def get_general_ledger():
    """
    Get General Ledger (Buku Besar) for a company and date range.
    Shows all transactions with debit and credit entries (double-entry).
    Each transaction shows both COA entries together.
    """
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    # Get parameters
    company_id = request.args.get('company_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    coa_code = request.args.get('coa_code')  # Optional: filter by specific COA
    
    if not company_id:
        return jsonify({'error': 'company_id is required'}), 400
    
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400
    
    try:
        with engine.connect() as conn:
            # Build query
            coa_filter = ""
            params = {
                'company_id': company_id,
                'start_date': start_date,
                'end_date': end_date
            }
            
            if coa_code:
                coa_filter = "AND coa.code = :coa_code"
                params['coa_code'] = coa_code
            
            # Query to get all transactions with their COA mappings
            # The key insight: mapping_type tells us which side of the entry
            # DEBIT mapping = this COA should be debited
            # CREDIT mapping = this COA should be credited
            # db_cr tells us the transaction direction from bank perspective
            # For GL, we use mapping_type to determine debit/credit
            query = text(f"""
                SELECT 
                    t.id as transaction_id,
                    t.txn_date,
                    t.description,
                    t.amount,
                    t.db_cr,
                    m.id as mark_id,
                    m.personal_use as mark_name,
                    coa.code as coa_code,
                    coa.name as coa_name,
                    coa.category as coa_category,
                    mcm.mapping_type,
                    -- Use mapping_type to determine debit/credit
                    -- DEBIT mapping = positive amount (debit)
                    -- CREDIT mapping = negative amount (credit)
                    CASE 
                        WHEN mcm.mapping_type = 'DEBIT' THEN t.amount
                        WHEN mcm.mapping_type = 'CREDIT' THEN -t.amount
                        ELSE 0
                    END as signed_amount
                FROM transactions t
                INNER JOIN marks m ON t.mark_id = m.id
                INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                WHERE t.txn_date BETWEEN :start_date AND :end_date
                  AND t.company_id = :company_id
                  {coa_filter}
                ORDER BY t.txn_date, t.id, mcm.mapping_type
            """)
            
            result = conn.execute(query, params)
            
            # Process results - group by transaction first
            transactions = {}
            coa_balances = {}
            
            for row in result:
                d = dict(row._mapping)
                txn_id = d['transaction_id']
                
                if txn_id not in transactions:
                    transactions[txn_id] = {
                        'transaction_id': txn_id,
                        'txn_date': d['txn_date'].strftime('%Y-%m-%d') if isinstance(d['txn_date'], datetime) else str(d['txn_date']),
                        'description': d['description'] or '',
                        'mark_name': d['mark_name'] or '',
                        'amount': float(d['amount'] or 0),
                        'db_cr': d['db_cr'],
                        'entries': []
                    }
                
                coa_code = d['coa_code']
                signed_amount = float(d['signed_amount'] or 0)
                
                # Add entry
                transactions[txn_id]['entries'].append({
                    'coa_code': coa_code,
                    'coa_name': d['coa_name'],
                    'coa_category': d['coa_category'],
                    'mapping_type': d['mapping_type'],
                    'debit': signed_amount if signed_amount > 0 else 0,
                    'credit': abs(signed_amount) if signed_amount < 0 else 0,
                    'signed_amount': signed_amount
                })
            
            # Now build COA groups with running balance
            coa_groups = {}
            
            for txn in transactions.values():
                for entry in txn['entries']:
                    coa_code = entry['coa_code']
                    
                    if coa_code not in coa_groups:
                        coa_groups[coa_code] = {
                            'coa_code': coa_code,
                            'coa_name': entry['coa_name'],
                            'coa_category': entry['coa_category'],
                            'transactions': [],
                            'total_debit': 0,
                            'total_credit': 0,
                            'ending_balance': 0
                        }
                    
                    # Calculate running balance
                    if 'running_balance' not in coa_groups[coa_code]:
                        coa_groups[coa_code]['running_balance'] = 0
                    
                    coa_groups[coa_code]['running_balance'] += entry['signed_amount']
                    
                    # Add transaction with all its entries to this COA group
                    coa_groups[coa_code]['transactions'].append({
                        'transaction_id': txn['transaction_id'],
                        'txn_date': txn['txn_date'],
                        'description': txn['description'],
                        'mark_name': txn['mark_name'],
                        'amount': txn['amount'],
                        'db_cr': txn['db_cr'],
                        'entries': txn['entries'],
                        'current_entry': {
                            'coa_code': entry['coa_code'],
                            'debit': entry['debit'],
                            'credit': entry['credit'],
                            'running_balance': coa_groups[coa_code]['running_balance']
                        }
                    })
                    
                    coa_groups[coa_code]['total_debit'] += entry['debit']
                    coa_groups[coa_code]['total_credit'] += entry['credit']
                    coa_groups[coa_code]['ending_balance'] = coa_groups[coa_code]['running_balance']
            
            # Convert to list and format transactions
            coa_groups_list = []
            for coa_code, group in coa_groups.items():
                # Format transactions to show all entries
                formatted_transactions = []
                seen_txns = set()
                
                for txn in group['transactions']:
                    if txn['transaction_id'] not in seen_txns:
                        seen_txns.add(txn['transaction_id'])
                        formatted_transactions.append({
                            'transaction_id': txn['transaction_id'],
                            'txn_date': txn['txn_date'],
                            'description': txn['description'],
                            'mark_name': txn['mark_name'],
                            'amount': txn['amount'],
                            'db_cr': txn['db_cr'],
                            'entries': txn['entries'],
                            'current_entry': txn['current_entry']
                        })
                
                coa_groups_list.append({
                    'coa_code': group['coa_code'],
                    'coa_name': group['coa_name'],
                    'coa_category': group['coa_category'],
                    'transactions': formatted_transactions,
                    'total_debit': group['total_debit'],
                    'total_credit': group['total_credit'],
                    'ending_balance': group['ending_balance']
                })
            
            # Calculate grand totals
            grand_total_debit = sum(g['total_debit'] for g in coa_groups_list)
            grand_total_credit = sum(g['total_credit'] for g in coa_groups_list)
            
            return jsonify({
                'success': True,
                'data': {
                    'company_id': company_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'coa_groups': coa_groups_list,
                    'total_accounts': len(coa_groups_list),
                    'total_transactions': len(transactions),
                    'grand_total_debit': grand_total_debit,
                    'grand_total_credit': grand_total_credit,
                    'is_balanced': abs(grand_total_debit - grand_total_credit) < 0.01
                }
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@general_ledger_bp.route('/api/reports/general-ledger/export', methods=['GET'])
def export_general_ledger():
    """
    Export General Ledger to Excel or PDF format.
    """
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    # Get parameters
    company_id = request.args.get('company_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    coa_code = request.args.get('coa_code')  # Optional: filter by specific COA
    format_type = request.args.get('format', 'excel')  # excel or pdf
    
    if not company_id:
        return jsonify({'error': 'company_id is required'}), 400
    
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400
    
    try:
        # Get the same data as the regular report
        with engine.connect() as conn:
            # Build query
            coa_filter = ""
            params = {
                'company_id': company_id,
                'start_date': start_date,
                'end_date': end_date
            }
            
            if coa_code:
                coa_filter = "AND coa.code = :coa_code"
                params['coa_code'] = coa_code
            
            query = text(f"""
                SELECT 
                    t.id as transaction_id,
                    t.txn_date,
                    t.description,
                    t.amount,
                    t.db_cr,
                    m.id as mark_id,
                    m.personal_use as mark_name,
                    coa.code as coa_code,
                    coa.name as coa_name,
                    coa.category as coa_category,
                    mcm.mapping_type,
                    CASE 
                        WHEN mcm.mapping_type = 'DEBIT' THEN t.amount
                        WHEN mcm.mapping_type = 'CREDIT' THEN -t.amount
                        ELSE 0
                    END as signed_amount
                FROM transactions t
                INNER JOIN marks m ON t.mark_id = m.id
                INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                WHERE t.txn_date BETWEEN :start_date AND :end_date
                  AND t.company_id = :company_id
                  {coa_filter}
                ORDER BY t.txn_date, t.id, mcm.mapping_type
            """)
            
            result = conn.execute(query, params)
            
            # Process results - group by transaction first
            transactions = {}
            coa_groups = {}
            
            for row in result:
                d = dict(row._mapping)
                txn_id = d['transaction_id']
                
                if txn_id not in transactions:
                    transactions[txn_id] = {
                        'transaction_id': txn_id,
                        'txn_date': d['txn_date'].strftime('%Y-%m-%d') if isinstance(d['txn_date'], datetime) else str(d['txn_date']),
                        'description': d['description'] or '',
                        'mark_name': d['mark_name'] or '',
                        'amount': float(d['amount'] or 0),
                        'db_cr': d['db_cr'],
                        'entries': []
                    }
                
                coa_code = d['coa_code']
                signed_amount = float(d['signed_amount'] or 0)
                
                # Add entry
                transactions[txn_id]['entries'].append({
                    'coa_code': coa_code,
                    'coa_name': d['coa_name'],
                    'coa_category': d['coa_category'],
                    'mapping_type': d['mapping_type'],
                    'debit': signed_amount if signed_amount > 0 else 0,
                    'credit': abs(signed_amount) if signed_amount < 0 else 0,
                    'signed_amount': signed_amount
                })
            
            # Build COA groups with running balance
            for txn in transactions.values():
                for entry in txn['entries']:
                    coa_code = entry['coa_code']
                    
                    if coa_code not in coa_groups:
                        coa_groups[coa_code] = {
                            'coa_code': coa_code,
                            'coa_name': entry['coa_name'],
                            'coa_category': entry['coa_category'],
                            'transactions': [],
                            'total_debit': 0,
                            'total_credit': 0,
                            'ending_balance': 0
                        }
                    
                    # Calculate running balance
                    if 'running_balance' not in coa_groups[coa_code]:
                        coa_groups[coa_code]['running_balance'] = 0
                    
                    coa_groups[coa_code]['running_balance'] += entry['signed_amount']
                    
                    # Add transaction with all its entries to this COA group
                    coa_groups[coa_code]['transactions'].append({
                        'transaction_id': txn['transaction_id'],
                        'txn_date': txn['txn_date'],
                        'description': txn['description'],
                        'mark_name': txn['mark_name'],
                        'amount': txn['amount'],
                        'db_cr': txn['db_cr'],
                        'entries': txn['entries'],
                        'current_entry': {
                            'coa_code': entry['coa_code'],
                            'debit': entry['debit'],
                            'credit': entry['credit'],
                            'running_balance': coa_groups[coa_code]['running_balance']
                        }
                    })
                    
                    coa_groups[coa_code]['total_debit'] += entry['debit']
                    coa_groups[coa_code]['total_credit'] += entry['credit']
                    coa_groups[coa_code]['ending_balance'] = coa_groups[coa_code]['running_balance']
        
        if format_type == 'excel':
            return export_to_excel(coa_groups, company_id, start_date, end_date)
        else:
            return jsonify({'error': 'PDF export not yet implemented'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def export_to_excel(coa_groups, company_id, start_date, end_date):
    """
    Export General Ledger to Excel format.
    """
    try:
        # Create a BytesIO buffer
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Create summary sheet
            summary_data = []
            for coa_code, group in coa_groups.items():
                summary_data.append({
                    'COA Code': group['coa_code'],
                    'COA Name': group['coa_name'],
                    'Category': group['coa_category'],
                    'Total Debit': group['total_debit'],
                    'Total Credit': group['total_credit'],
                    'Ending Balance': group['ending_balance']
                })
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Create detailed sheets for each COA
            for coa_code, group in coa_groups.items():
                detailed_data = []
                
                for txn in group['transactions']:
                    for entry in txn['entries']:
                        if entry['coa_code'] == coa_code:  # Only show entries for this COA
                            detailed_data.append({
                                'Tanggal': txn['txn_date'],
                                'Deskripsi': txn['description'],
                                'Mark': txn['mark_name'],
                                'COA': entry['coa_code'],
                                'Debit': entry['debit'] if entry['debit'] > 0 else 0,
                                'Kredit': entry['credit'] if entry['credit'] > 0 else 0,
                                'Saldo': entry['current_entry']['running_balance'] if entry['current_entry'] else 0
                            })
                
                if detailed_data:
                    detailed_df = pd.DataFrame(detailed_data)
                    # Sanitize sheet name (Excel sheet names have restrictions)
                    sheet_name = f"{coa_code}_{group['coa_name']}"[:31]  # Max 31 chars
                    sheet_name = sheet_name.replace('/', '_').replace('\\', '_')
                    detailed_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        output.seek(0)
        
        # Create response
        response = make_response(send_file(
            output,
            as_attachment=True,
            download_name=f'general_ledger_{company_id}_{start_date}_to_{end_date}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ))
        
        return response
    
    except Exception as e:
        return jsonify({'error': f'Failed to create Excel file: {str(e)}'}), 500


@general_ledger_bp.route('/api/reports/general-ledger/summary', methods=['GET'])
def get_general_ledger_summary():
    """
    Get General Ledger Summary - COA balances for a period.
    """
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    company_id = request.args.get('company_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not company_id:
        return jsonify({'error': 'company_id is required'}), 400
    
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    coa.code as coa_code,
                    coa.name as coa_name,
                    coa.category as coa_category,
                    SUM(
                        CASE 
                            WHEN mcm.mapping_type = 'DEBIT' THEN t.amount
                            WHEN mcm.mapping_type = 'CREDIT' THEN -t.amount
                            ELSE 0
                        END
                    ) as balance,
                    SUM(CASE WHEN mcm.mapping_type = 'DEBIT' THEN t.amount ELSE 0 END) as total_debit,
                    SUM(CASE WHEN mcm.mapping_type = 'CREDIT' THEN t.amount ELSE 0 END) as total_credit,
                    COUNT(DISTINCT t.id) as transaction_count
                FROM transactions t
                INNER JOIN marks m ON t.mark_id = m.id
                INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                WHERE t.txn_date BETWEEN :start_date AND :end_date
                  AND t.company_id = :company_id
                GROUP BY coa.code, coa.name, coa.category
                HAVING balance != 0
                ORDER BY coa.code
            """)
            
            result = conn.execute(query, {
                'company_id': company_id,
                'start_date': start_date,
                'end_date': end_date
            })
            
            summary = []
            for row in result:
                d = dict(row._mapping)
                summary.append({
                    'coa_code': d['coa_code'],
                    'coa_name': d['coa_name'],
                    'coa_category': d['coa_category'],
                    'balance': float(d['balance'] or 0),
                    'total_debit': float(d['total_debit'] or 0),
                    'total_credit': float(d['total_credit'] or 0),
                    'transaction_count': d['transaction_count']
                })
            
            return jsonify({
                'success': True,
                'data': {
                    'company_id': company_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'accounts': summary,
                    'total_accounts': len(summary)
                }
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
