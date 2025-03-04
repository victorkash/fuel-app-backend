from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os

app = Flask(__name__)

# Configure CORS
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "https://ammica.netlify.app",
                "https://67c4b0d1068a0639edffac27--ammica.netlify.app",
                "http://localhost:3000"
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    }
)

# Updated database connection with error handling
def get_db_connection():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(database_url)

# Database initialization with app context
def init_db():
    try:
        with app.app_context():
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sales (
                        id SERIAL PRIMARY KEY,
                        fuel_type TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        price REAL NOT NULL,
                        date TEXT NOT NULL
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS customers (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        points INTEGER DEFAULT 0
                    )
                ''')
                conn.commit()
    except Exception as e:
        app.logger.error(f"Database initialization failed: {str(e)}")
        raise

# Initialize database when app starts
@app.before_first_request
def initialize_db():
    init_db()

@app.route('/')
def home():
    return "Welcome to Fuel Management App!"

# Sales endpoint with error handling
@app.route('/api/sales', methods=['POST'])
def log_sale():
    try:
        data = request.json
        required_fields = ['fuel_type', 'quantity', 'price', 'date']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sales (fuel_type, quantity, price, date)
                VALUES (%s, %s, %s, %s)
            ''', (data['fuel_type'], data['quantity'], data['price'], data['date']))
            conn.commit()
            
        return jsonify({"message": "Sale logged successfully"}), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Updated customers endpoint with unique constraint
@app.route('/api/customers', methods=['POST'])
def add_customer():
    try:
        data = request.json
        if 'name' not in data or not data['name'].strip():
            return jsonify({"error": "Customer name is required"}), 400
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO customers (name)
                VALUES (%s)
                ON CONFLICT (name) DO NOTHING
            ''', (data['name'].strip(),))
            conn.commit()
            
            if cursor.rowcount == 0:
                return jsonify({"warning": "Customer already exists"}), 200
                
        return jsonify({"message": "Customer added successfully"}), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Reward points endpoint with validation
@app.route('/api/reward', methods=['POST'])
def update_rewards():
    try:
        data = request.json
        if 'name' not in data or 'points' not in data:
            return jsonify({"error": "Name and points are required"}), 400
            
        points = int(data['points'])
        if points <= 0:
            return jsonify({"error": "Points must be a positive integer"}), 400
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE customers
                SET points = points + %s
                WHERE name = %s
            ''', (points, data['name']))
            conn.commit()
            
            if cursor.rowcount == 0:
                return jsonify({"error": "Customer not found"}), 404
                
        return jsonify({"message": "Points updated successfully"}), 200
        
    except ValueError:
        return jsonify({"error": "Invalid points value"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Sales reports endpoints with parameter validation
@app.route('/api/sales_by_type', methods=['GET'])
def sales_by_type():
    try:
        filter_type = request.args.get('filter', 'alltime')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        base_query = '''
            SELECT fuel_type, SUM(quantity) AS total_quantity
            FROM sales
        '''
        params = []
        
        if filter_type == 'custom':
            if not start_date or not end_date:
                return jsonify({"error": "Both start_date and end_date are required for custom filter"}), 400
            base_query += " WHERE date BETWEEN %s AND %s"
            params.extend([start_date, end_date])
            
        base_query += " GROUP BY fuel_type"
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(base_query, params)
            results = cursor.fetchall()
            
        return jsonify([{
            "fuel_type": row[0],
            "total_quantity": float(row[1])
        } for row in results])
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sales_over_time', methods=['GET'])
def sales_over_time():
    try:
        filter_type = request.args.get('filter', 'alltime')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        base_query = '''
            SELECT date, SUM(quantity * price) AS total_sales
            FROM sales
        '''
        params = []
        
        if filter_type == 'custom':
            if not start_date or not end_date:
                return jsonify({"error": "Both start_date and end_date are required for custom filter"}), 400
            base_query += " WHERE date BETWEEN %s AND %s"
            params.extend([start_date, end_date])
            
        base_query += " GROUP BY date ORDER BY date ASC"
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(base_query, params)
            results = cursor.fetchall()
            
        return jsonify([{
            "date": row[0],
            "total_sales": float(row[1])
        } for row in results])
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports', methods=['GET'])
def generate_reports():
    try:
        filter_type = request.args.get('filter', 'alltime')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        base_query = '''
            SELECT 
                fuel_type,
                SUM(quantity) AS total_quantity,
                SUM(quantity * price) AS total_revenue
            FROM sales
        '''
        params = []
        
        if filter_type == 'custom':
            if not start_date or not end_date:
                return jsonify({"error": "Both start_date and end_date are required for custom filter"}), 400
            base_query += " WHERE date BETWEEN %s AND %s"
            params.extend([start_date, end_date])
            
        base_query += " GROUP BY fuel_type"
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(base_query, params)
            results = cursor.fetchall()
            
        return jsonify([{
            "fuel_type": row[0],
            "total_quantity": float(row[1]),
            "total_revenue": float(row[2])
        } for row in results])
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
