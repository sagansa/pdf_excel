from flask import Flask, jsonify, request
from db.session import get_db_engine
from sqlalchemy import text
import json

app = Flask(__name__)

@app.route('/debug/amortization', methods=['GET'])
def debug_amortization():
    try:
        company_id = request.args.get('company_id', '8ab69d4a-e591-4f05-909e-25ff12352efb')
        year = request.args.get('year', '2025')
        
        engine, _ = get_db_engine()
        with engine.connect() as conn:
            # Test the problematic query
            query = '''
                SELECT DISTINCT
                    t.id as asset_id, t.txn_date, t.description,
                    t.amount as acquisition_cost, t.amortization_asset_group_id as asset_group_id,
                    t.amortization_start_date, t.use_half_rate, t.amortization_notes as notes,
                    ag.group_name, ag.tarif_rate, ag.useful_life_years, ag.asset_type,
                    m.personal_use as mark_name,
                    coa.code as coa_code, coa.name as coa_name
                FROM transactions t
                INNER JOIN marks m ON t.mark_id = m.id
                INNER JOIN mark_coa_mapping mcm ON t.mark_id = mcm.mark_id
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                LEFT JOIN amortization_asset_groups ag ON t.amortization_asset_group_id = ag.id
                WHERE coa.code = '5314'
                AND (t.company_id = :company_id OR :company_id IS NULL)
                AND YEAR(t.txn_date) <= :year
                ORDER BY t.txn_date DESC
                LIMIT 5
            '''
            
            result = conn.execute(text(query), {'company_id': company_id, 'year': year})
            
            items = []
            for row in result:
                d = dict(row._mapping)
                items.append(d)
            
            return jsonify({
                'success': True,
                'count': len(items),
                'items': items
            })
            
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
