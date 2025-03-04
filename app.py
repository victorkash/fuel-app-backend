from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2  # PostgreSQL driver
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

# Database connection helper for PostgreSQL
def get_db_connection():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])  # Use Render's DATABASE_URL
    return conn

# Initialize database with PostgreSQL syntax
def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Sales table
        cursor.execute('''CREATE TABLE IF NOT EXISTS sales
                          (id SERIAL PRIMARY KEY,
                           fuel_type TEXT NOT NULL,
                           quantity REAL NOT NULL,
                           price REAL NOT NULL,
                           date TEXT NOT NULL)''')
        # Customers table
        cursor.execute('''CREATE TABLE IF NOT EXISTS customers
                          (id SERIAL PRIMARY KEY,
                           name TEXT NOT NULL,
                           points INTEGER DEFAULT 0)''')
        conn.commit()

init_db()

@app.route('/')
def home():
    return "Welcome to Fuel Management App!"

# Sales endpoint
@app.route('/api/sales', methods=['POST'])
def sales():
    try:
        data = request.json
        if not all(key in data for key in ['fuel_type', 'quantity', 'price', 'date']):
            return jsonify({"error": "Missing data"}), 400
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO sales (fuel_type, quantity, price, date) VALUES (%s, %s, %s, %s)",
                           (data['fuel_type'], data['quantity'], data['price'], data['date']))
            conn.commit()
        return jsonify({"message": "Sale logged"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Customers endpoint
@app.route('/api/customers', methods=['POST'])
def add_customer():
    data = request.json
    if 'name' not in data:
        return jsonify({"error": "Name is required"}), 400
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO customers (name, points) VALUES (%s, 0)", (data['name'],))
            conn.commit()
        return jsonify({"message": "Customer added"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Reward points endpoint
@app.route('/api/reward', methods=['POST'])
def reward():
    data = request.json
    if 'name' not in data or 'points' not in data:
        return jsonify({"error": "Name and points are required"}), 400
    try:
        points = int(data['points'])
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE customers SET points = points + %s WHERE name = %s", (points, data['name']))
            if cursor.rowcount == 0:
                return jsonify({"error": "Customer not found"}), 404
            conn.commit()
        return jsonify({"message": "Points added"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Sales by Fuel Type endpoint
@app.route('/api/sales_by_type', methods=['GET'])
def sales_by_type():
    filter_type = request.args.get('filter', 'alltime')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = "SELECT fuel_type, SUM(quantity) AS total_quantity FROM sales"
    params = []
    
    if filter_type == 'custom':
        if not start_date or not end_date:
            return jsonify({"error": "Start and end dates are required"}), 400
        query += " WHERE date BETWEEN %s AND %s"
        params.extend([start_date, end_date])
    
    query += " GROUP BY fuel_type"
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            data = cursor.fetchall()
        return jsonify([{"fuel_type": row[0], "total_quantity": row[1]} for row in data])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Sales Over Time endpoint
@app.route('/api/sales_over_time', methods=['GET'])
def sales_over_time():
    filter_type = request.args.get('filter', 'alltime')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = "SELECT date, SUM(quantity * price) AS total_sales FROM sales"
    params = []
    
    if filter_type == 'custom':
        if not start_date or not end_date:
            return jsonify({"error": "Start and end dates are required"}), 400
        query += " WHERE date BETWEEN %s AND %s"
        params.extend([start_date, end_date])
    
    query += " GROUP BY date ORDER BY date ASC"
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            data = cursor.fetchall()
        return jsonify([{"date": row[0], "total_sales": row[1]} for row in data])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Reports endpoint
@app.route('/api/reports', methods=['GET'])
def reports():
    filter_type = request.args.get('filter', 'alltime')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = "SELECT fuel_type, SUM(quantity) AS total_quantity, SUM(quantity * price) AS total_revenue FROM sales"
    params = []
    
    if filter_type == 'custom':
        if not start_date or not end_date:
            return jsonify({"error": "Start and end dates are required"}), 400
        query += " WHERE date BETWEEN %s AND %s"
        params.extend([start_date, end_date])
    
    query += " GROUP BY fuel_type"
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            data = cursor.fetchall()
        return jsonify([{"fuel_type": row[0], "total_quantity": row[1], "total_revenue": row[2]} for row in data])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
