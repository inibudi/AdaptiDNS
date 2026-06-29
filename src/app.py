#!/usr/bin/env python3
import sys
import os
import json
from datetime import datetime, date
from decimal import Decimal

# FIX PYTHON PATH - Absolute path
sys.path.insert(0, '/opt/bandwidth-monitor')

try:
    from config.config import Config
    print("✅ Config imported successfully")
except ImportError as e:
    print(f"❌ Config import error: {e}")
    # Fallback: Set config manually
    class Config:
        DB_HOST = 'localhost'
        DB_USER = 'bandwidth_user'
        DB_PASSWORD = 'secure_password_123'
        DB_NAME = 'bandwidth_monitorsp'
        API_HOST = '192.168.1.253'
        API_PORT = 5001

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import pymysql
import threading
import time

# 🎯 FIX: Enhanced JSON encoder untuk handle Decimal dan datetime
class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)

# Initialize Flask app FIRST
app = Flask(__name__)
app.config['SECRET_KEY'] = 'bandwidth-secret-key'
app.json_encoder = EnhancedJSONEncoder  # 🎯 Use enhanced encoder
socketio = SocketIO(app, json=json)

class Dashboard:
    def __init__(self):
        print("🚀 Initializing Enhanced Dashboard...")
        self.setup_database()
    
    def setup_database(self):
        """Setup database connection"""
        try:
            self.db = pymysql.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            print("✅ Dashboard database connected")
        except Exception as e:
            print(f"❌ Dashboard database error: {e}")
            self.db = None
    
    def get_stats(self):
        """Get comprehensive statistics - BYPASS active_sessions"""
        if not self.db:
            return self.get_empty_stats()
            
        try:
            with self.db.cursor() as cursor:
                # Total queries (24 jam terakhir)
                cursor.execute("""
                    SELECT COUNT(*) as total 
                    FROM user_access 
                    WHERE access_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                """)
                total_queries = cursor.fetchone()['total']
                
                # Active penalties - langsung dari penalty_logs
                cursor.execute("""
                    SELECT COUNT(DISTINCT username) as active 
                    FROM penalty_logs 
                    WHERE status = 'active'
                    AND applied_at >= DATE_SUB(NOW(), INTERVAL 30 MINUTE)
                """)
                active_penalties = cursor.fetchone()['active']
                
                # Total penalties applied
                cursor.execute("""
                    SELECT COUNT(*) as total 
                    FROM penalty_logs 
                    WHERE status IN ('active', 'reset')
                """)
                penalties_applied = cursor.fetchone()['total']
                
                # 🎯 FIX: Active sessions dari user_access (INSTANT)
                cursor.execute("""
                    SELECT COUNT(DISTINCT username) as sessions 
                    FROM user_access 
                    WHERE access_time >= DATE_SUB(NOW(), INTERVAL 10 MINUTE)
                    AND username NOT LIKE '%unknown%'
                """)
                active_sessions = cursor.fetchone()['sessions']
                
                # Classification stats
                cursor.execute("""
                    SELECT classification, COUNT(*) as count 
                    FROM user_access 
                    WHERE classification IS NOT NULL 
                    AND access_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                    GROUP BY classification
                """)
                classification_stats = cursor.fetchall()
                
                # Recent activity
                cursor.execute("""
                    SELECT username, domain, classification, 
                           DATE_FORMAT(access_time, '%H:%i:%s') as access_time_str
                    FROM user_access 
                    ORDER BY access_time DESC 
                    LIMIT 10
                """)
                recent_activity = cursor.fetchall()
                
                print(f"📊 Stats: queries={total_queries}, penalties={active_penalties}, total_penalties={penalties_applied}, sessions={active_sessions}")
                
                return {
                    'total_queries': total_queries,
                    'active_penalties': active_penalties,
                    'penalties_applied': penalties_applied,
                    'active_sessions': active_sessions,
                    'classification_stats': classification_stats,
                    'recent_activity': recent_activity
                }
        except Exception as e:
            print(f"❌ Database query error: {e}")
            return self.get_empty_stats()
    
    def get_empty_stats(self):
        """Return empty stats when database unavailable"""
        return {
            'total_queries': 0,
            'active_penalties': 0,
            'penalties_applied': 0,
            'active_sessions': 0,
            'classification_stats': [],
            'recent_activity': []
        }
    
    def get_penalty_logs(self, limit=50):
        """Get penalty logs data - FIXED DATE_FORMAT"""
        if not self.db:
            return []
            
        try:
            with self.db.cursor() as cursor:
                # 🎯 FIX: Gunakan parameterized query dengan benar
                cursor.execute("""
                    SELECT 
                        id, username, ip_address, penalty_type,
                        bandwidth_before, bandwidth_after,
                        DATE_FORMAT(applied_at, '%%Y-%%m-%%d %%H:%%i:%%s') as applied_at_str,
                        DATE_FORMAT(reset_at, '%%Y-%%m-%%d %%H:%%i:%%s') as reset_at_str,
                        status
                    FROM penalty_logs 
                    ORDER BY applied_at DESC 
                    LIMIT %s
                """, (limit,))
                results = cursor.fetchall()
                return results
        except Exception as e:
            print(f"❌ Penalty logs query error: {e}")
            return []

    # Dalam method get_user_access_logs(), perbaiki query:
    def get_user_access_logs(self, limit=50):
        """Get user access logs - FIXED DATE_FORMAT"""
        if not self.db:
            return []
            
        try:
            with self.db.cursor() as cursor:
                # 🎯 FIX: Gunakan double %%
                cursor.execute("""
                    SELECT 
                        id, username, ip_address, domain, 
                        classification, confidence,
                        DATE_FORMAT(access_time, '%%H:%%i:%%s') as access_time_str,
                        penalty_applied, status
                    FROM user_access 
                    ORDER BY access_time DESC 
                    LIMIT %s
                """, (limit,))
                results = cursor.fetchall()
                return results
        except Exception as e:
            print(f"❌ User access query error: {e}")
            return []

    # Dalam method get_penalty_monitoring(), perbaiki query:
    def get_penalty_monitoring(self, limit=50):
        """Get penalty monitoring data - FIXED DATE_FORMAT"""
        if not self.db:
            return []
        
        try:
            with self.db.cursor() as cursor:
                # 🎯 FIX: Gunakan double %%
                cursor.execute("""
                    SELECT 
                        username, ip_address, domain,
                        classification, confidence,
                        DATE_FORMAT(access_time, '%%H:%%i:%%s') as access_time,
                        COALESCE(current_bandwidth, '10M/10M') as current_bandwidth,
                        penalty_status
                    FROM penalty_monitoring 
                    ORDER BY access_time DESC 
                    LIMIT %s
                """, (limit,))
                results = cursor.fetchall()
                return results
        except Exception as e:
            print(f"❌ Penalty monitoring query error: {e}")
            return []

# Initialize dashboard AFTER app is defined
dashboard = Dashboard()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard_home():
    return render_template('index.html')

@app.route('/penalty-logs')
def penalty_logs():
    return render_template('penalty_logs.html')

@app.route('/user-access')
def user_access():
    return render_template('user_access.html')

@app.route('/penalty-monitoring')
def penalty_monitoring():
    return render_template('penalty_monitoring.html')

# API Endpoints dengan error handling
@app.route('/api/stats')
def get_stats():
    try:
        stats = dashboard.get_stats()
        return jsonify(stats)
    except Exception as e:
        print(f"❌ API Stats Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/penalty-logs')
def api_penalty_logs():
    try:
        limit = request.args.get('limit', 50, type=int)
        logs = dashboard.get_penalty_logs(limit)
        print(f"📊 API Penalty Logs: Returning {len(logs)} records")
        return jsonify(logs)
    except Exception as e:
        print(f"❌ API Penalty Logs Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/user-access')
def api_user_access():
    try:
        limit = request.args.get('limit', 50, type=int)
        logs = dashboard.get_user_access_logs(limit)
        print(f"📊 API User Access: Returning {len(logs)} records")
        return jsonify(logs)
    except Exception as e:
        print(f"❌ API User Access Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/penalty-monitoring')
def api_penalty_monitoring():
    try:
        limit = request.args.get('limit', 50, type=int)
        data = dashboard.get_penalty_monitoring(limit)
        print(f"📊 API Penalty Monitoring: Returning {len(data)} records")
        return jsonify(data)
    except Exception as e:
        print(f"❌ API Penalty Monitoring Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# SocketIO for real-time updates
@socketio.on('connect')
def handle_connect():
    print('✅ Client connected to dashboard')
    try:
        stats = dashboard.get_stats()
        socketio.emit('stats_update', stats)
    except Exception as e:
        print(f"❌ Error sending initial stats: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    print('❌ Client disconnected from dashboard')

def background_stats_update():
    """Background thread untuk real-time updates"""
    print("🔄 Starting background stats update thread...")
    while True:
        try:
            # 🎯 FIX: Get fresh stats every 5 seconds
            stats = dashboard.get_stats()
            # 🎯 FIX: Emit to all connected clients
            socketio.emit('stats_update', stats)
            print("🔄 Stats updated and emitted to clients")
            time.sleep(5)
        except Exception as e:
            print(f"❌ Dashboard update error: {e}")
            time.sleep(10)

if __name__ == '__main__':
    print("🚀 Starting Enhanced Bandwidth Dashboard...")
    
    # Start background thread
    update_thread = threading.Thread(target=background_stats_update, daemon=True)
    update_thread.start()
    
    # Run app
    print(f"📊 Dashboard available at: http://{Config.API_HOST}:{Config.API_PORT}")
    socketio.run(app, 
                 host=Config.API_HOST, 
                 port=Config.API_PORT, 
                 debug=True, 
                 allow_unsafe_werkzeug=True)