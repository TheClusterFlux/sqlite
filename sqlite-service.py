from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os

app = Flask(__name__)

# Define the SQLite database file location (using persistent storage in Kubernetes)
DATABASE = '/app/data/database.db'

# Ensure the database file exists
def init_db():
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)')
        conn.commit()
        conn.close()
        
@app.before_request
def block_public_access():
    if request.host == 'sqlitedb.theclusterflux.com' and request.path not in ['/status', '/']:
        return jsonify({"error": "Access forbidden"}), 403

@app.route('/execute', methods=['POST'])
def execute_sql():
    sql_query = request.json.get('query', None)
    if not sql_query:
        return jsonify({"error": "No SQL query provided"}), 400
    
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        conn.commit()
        if sql_query.strip().lower().startswith("insert"):
            result = {"lastrowid": cursor.lastrowid}
        else:
            result = {"result": cursor.fetchall()}
        conn.close()
        return jsonify(result), 200
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
        tables = cursor.fetchall()
        
        table_overview = {}
        for table in tables:
            table_name = table[0]
            output_table_name = table_name.replace('_', ' ')
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            record_count = cursor.fetchone()[0]
            
            cursor.execute(f'PRAGMA table_info({table_name})')
            columns = cursor.fetchall()
            output_column_names = [col[1].replace('_', ' ') for col in columns]
            
            cursor.execute(f'SELECT * FROM {table_name}')
            rows = cursor.fetchall()
            total_size = sum(len(str(row)) for row in rows)

            
            table_overview[output_table_name] = {
                "record_count": record_count,
                "total_size": total_size,
                "columns": output_column_names
            }
        
        conn.close()
        return jsonify({"status": "ok", "tables": table_overview}), 200
    except sqlite3.Error as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/')
def home():
    return send_from_directory('templates', 'index.html')

if __name__ == '__main__':
    init_db()  # Initialize the DB if not already initialized
    app.run(host='0.0.0.0', port=8080)
