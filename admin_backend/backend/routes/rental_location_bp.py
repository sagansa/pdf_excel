import datetime
import uuid

from flask import Blueprint, jsonify, request
from sqlalchemy import text

from backend.errors import BadRequestError, NotFoundError
from backend.routes.rental_helpers import require_db_engine, serialize_row
from backend.routes.rental_queries import build_locations_query

rental_location_bp = Blueprint('rental_location_bp', __name__)


@rental_location_bp.route('/api/rental-locations', methods=['GET'])
def get_locations():
    company_id = request.args.get('company_id')
    engine = require_db_engine()
    with engine.connect() as conn:
        result = conn.execute(build_locations_query(), {'company_id': company_id})
        locations = [serialize_row(row) for row in result]
    return jsonify({'locations': locations})


@rental_location_bp.route('/api/rental-locations', methods=['POST'])
def create_location():
    data = request.json or {}
    engine = require_db_engine()

    if not data.get('company_id') or not data.get('location_name'):
        raise BadRequestError('company_id and location_name are required')

    location_id = str(uuid.uuid4())
    now = datetime.datetime.now()

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO rental_locations (
                id, company_id, location_name, address, city, province,
                postal_code, latitude, longitude, area_sqm, notes, created_at, updated_at
            ) VALUES (
                :id, :company_id, :location_name, :address, :city, :province,
                :postal_code, :latitude, :longitude, :area_sqm, :notes, :created_at, :updated_at
            )
        """), {
            'id': location_id,
            'company_id': data['company_id'],
            'location_name': data['location_name'],
            'address': data.get('address'),
            'city': data.get('city'),
            'province': data.get('province'),
            'postal_code': data.get('postal_code'),
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude'),
            'area_sqm': data.get('area_sqm'),
            'notes': data.get('notes'),
            'created_at': now,
            'updated_at': now
        })
    return jsonify({'id': location_id, 'message': 'Location created successfully'}), 201


@rental_location_bp.route('/api/rental-locations/<location_id>', methods=['PUT'])
def update_location(location_id):
    data = request.json or {}
    engine = require_db_engine()
    now = datetime.datetime.now()

    with engine.begin() as conn:
        result = conn.execute(text("""
            UPDATE rental_locations
            SET location_name = :location_name,
                address = :address,
                city = :city,
                province = :province,
                postal_code = :postal_code,
                latitude = :latitude,
                longitude = :longitude,
                area_sqm = :area_sqm,
                notes = :notes,
                updated_at = :updated_at
            WHERE id = :id
        """), {
            'id': location_id,
            'location_name': data.get('location_name'),
            'address': data.get('address'),
            'city': data.get('city'),
            'province': data.get('province'),
            'postal_code': data.get('postal_code'),
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude'),
            'area_sqm': data.get('area_sqm'),
            'notes': data.get('notes'),
            'updated_at': now
        })
        if int(result.rowcount or 0) == 0:
            raise NotFoundError('Location not found')
    return jsonify({'message': 'Location updated successfully'})


@rental_location_bp.route('/api/rental-locations/<location_id>', methods=['DELETE'])
def delete_location(location_id):
    engine = require_db_engine()
    with engine.begin() as conn:
        result = conn.execute(text("DELETE FROM rental_locations WHERE id = :id"), {'id': location_id})
        if int(result.rowcount or 0) == 0:
            raise NotFoundError('Location not found')
    return jsonify({'message': 'Location deleted successfully'})
