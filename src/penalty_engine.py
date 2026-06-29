#!/usr/bin/env python3
import pymysql
import time
import threading
from datetime import datetime
from config.config import Config

class SimplePenaltyEngine:
    def __init__(self):
        print("🚀 Initializing Simple Penalty Engine...")
        self.setup_database()
        # 🎯 UPDATED: Gunakan penalty rules dari Config
        self.penalty_rules = Config.PENALTY_RULES
        print(f"🎯 Loaded penalty rules: {self.penalty_rules}")
    
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
            print("✅ Penalty engine database connected")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            self.db = None
    
    def process_new_classifications(self):
        """Process new classifications dan apply penalty - FIXED VERSION"""
        try:
            with self.db.cursor() as cursor:
                # 🎯 Cari queries dengan status 'processed' dan belum ada penalty
                cursor.execute("""
                    SELECT ua.id, ua.username, ua.ip_address, ua.domain, 
                           ua.classification, ua.confidence
                    FROM user_access ua
                    WHERE ua.classification IS NOT NULL 
                    AND ua.penalty_applied = 0
                    AND ua.status = 'processed'
                    AND ua.confidence >= 0.80  -- Hanya yang confidence tinggi
                    AND ua.classification != 'whitelist'  -- Skip whitelist
                    ORDER BY ua.access_time DESC
                    LIMIT 10
                """)
                
                new_queries = cursor.fetchall()
                print(f"🔍 Found {len(new_queries)} queries needing penalty")
                
                for query in new_queries:
                    print(f"🎯 Processing penalty for: {query['username']} -> {query['classification']} (conf: {query['confidence']:.2f})")
                    
                    # Apply penalty berdasarkan classification
                    success = self.apply_penalty(
                        query['ip_address'],
                        query['username'], 
                        query['classification'],
                        query['confidence'] or 0.0
                    )
                    
                    if success:
                        # 🎯 Update status dengan benar
                        cursor.execute("""
                            UPDATE user_access 
                            SET penalty_applied = 1, 
                                penalty_type = %s,
                                status = 'penalized'
                            WHERE id = %s
                        """, (
                            query['classification'], 
                            query['id']
                        ))
                        
                        self.db.commit()
                        print(f"✅ Penalty applied and recorded: {query['username']} -> {query['classification']}")
                    else:
                        print(f"❌ Penalty failed: {query['username']}")
                        
        except Exception as e:
            print(f"❌ Penalty processing error: {e}")
            import traceback
            traceback.print_exc()
            if self.db:
                self.db.rollback()
    
    def apply_penalty(self, ip_address, username, classification, confidence):
        """Apply bandwidth penalty - SIMULATION MODE"""
        try:
            # 🎯 UPDATED: Gunakan rules dari Config
            penalty_bandwidth = self.penalty_rules.get(classification, '10M/10M')
            
            print(f"⚡ APPLYING PENALTY: {username} ({ip_address})")
            print(f"   Classification: {classification} (confidence: {confidence:.2f})")
            print(f"   Bandwidth: {penalty_bandwidth}")
            print(f"   Rule: {self.penalty_rules[classification]}")
            
            # 🎯 TODO: Integrasi dengan Mikrotik API di sini
            # self.apply_mikrotik_penalty(ip_address, penalty_bandwidth, username)
            
            # Log ke bandwidth_logs
            self.log_penalty_action(username, ip_address, classification, penalty_bandwidth)
            
            return True
            
        except Exception as e:
            print(f"❌ Penalty application error: {e}")
            return False
    
    def apply_mikrotik_penalty(self, ip_address, bandwidth, username):
        """Apply penalty ke Mikrotik - placeholder untuk integrasi"""
        print(f"📡 [Mikrotik] Would apply {bandwidth} to {username} ({ip_address})")
        # TODO: Implement Mikrotik API integration
        return True
    
    def log_penalty_action(self, username, ip_address, penalty_type, bandwidth):
        """Log penalty action ke database"""
        try:
            with self.db.cursor() as cursor:
                # Convert bandwidth ke numerik untuk logging
                bandwidth_numeric = self.convert_bandwidth_to_numeric(bandwidth)
                
                cursor.execute("""
                    INSERT INTO penalty_logs 
                    (username, ip_address, penalty_type, bandwidth_before, bandwidth_after, status)
                    VALUES (%s, %s, %s, %s, %s, 'active')
                """, (
                    username, 
                    ip_address, 
                    penalty_type, 
                    '10.0',  # 10M/10M dalam numerik (default)
                    bandwidth_numeric  # Nilai numerik penalty
                ))
                
                self.db.commit()
                print(f"📝 Penalty logged: {username} -> {penalty_type} ({bandwidth})")
                
        except Exception as e:
            print(f"❌ Penalty logging error: {e}")
    
    def convert_bandwidth_to_numeric(self, bandwidth_str):
        """Convert bandwidth string ke nilai numerik"""
        try:
            # Contoh: "5M/5M" -> 5.0, "7M/7M" -> 7.0
            if 'M' in bandwidth_str:
                # Ambil bagian download (sebelum slash)
                download_part = bandwidth_str.split('/')[0]
                # Hapus 'M' dan convert ke float
                numeric_value = float(download_part.replace('M', ''))
                return numeric_value
            return 10.0  # Default fallback
        except:
            return 10.0  # Default fallback
    
    def start_monitoring(self):
        """Start penalty monitoring"""
        print("🔧 Starting penalty engine monitoring...")
        
        def monitor_loop():
            while True:
                try:
                    self.process_new_classifications()
                    time.sleep(5)  # Check every 5 seconds
                except Exception as e:
                    print(f"❌ Monitor loop error: {e}")
                    time.sleep(10)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        print("✅ Penalty engine started")

# Test function
def test_penalty_engine():
    engine = SimplePenaltyEngine()
    engine.start_monitoring()
    
    # Keep running
    try:
        while True:
            time.sleep(10)
            print("💚 Penalty engine running...")
    except KeyboardInterrupt:
        print("🛑 Stopping penalty engine")

if __name__ == "__main__":
    test_penalty_engine()