#!/usr/bin/env python3
import time
import threading
import pymysql
from datetime import datetime, timedelta
# Di penalty_reset.py, tambahkan import Config
from config.config import Config

class PenaltyResetManager:
    def __init__(self):
        print("🔄 Initializing Penalty Reset Manager...")
        self.setup_database()
        self.reset_interval = 10 * 60  # 10 menit dalam detik
        self.normal_bandwidth = Config.PENALTY_RULES['whitelist']  # 🎯 Gunakan dari config
    
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
            print("✅ Reset manager database connected")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            self.db = None
    
    def check_and_reset_penalties(self):
        """Check dan reset penalties yang sudah melebihi 10 menit"""
        try:
            with self.db.cursor() as cursor:
                # Cari penalties yang sudah aktif lebih dari 10 menit
                cursor.execute("""
                    SELECT pl.id, pl.username, pl.ip_address, pl.penalty_type, pl.applied_at
                    FROM penalty_logs pl
                    WHERE pl.status = 'active'
                    AND pl.applied_at <= DATE_SUB(NOW(), INTERVAL 10 MINUTE)
                """)
                
                expired_penalties = cursor.fetchall()
                
                if expired_penalties:
                    print(f"🔄 Found {len(expired_penalties)} penalties to reset")
                    
                    for penalty in expired_penalties:
                        print(f"🎯 Resetting penalty for {penalty['username']} ({penalty['penalty_type']})")
                        
                        # Reset ke bandwidth normal
                        success = self.reset_to_normal_bandwidth(
                            penalty['ip_address'], 
                            penalty['username']
                        )
                        
                        if success:
                            # Update status di penalty_logs
                            cursor.execute("""
                                UPDATE penalty_logs 
                                SET status = 'reset', reset_at = NOW()
                                WHERE id = %s
                            """, (penalty['id'],))
                            
                            # Update user_access
                            cursor.execute("""
                                UPDATE user_access 
                                SET status = 'reset', 
                                    bandwidth_after = '10M/10M'
                                WHERE username = %s 
                                AND penalty_applied = 1
                                AND status = 'penalized'
                            """, (penalty['username'],))
                            
                            self.db.commit()
                            print(f"✅ Reset completed for {penalty['username']}")
                        else:
                            print(f"❌ Reset failed for {penalty['username']}")
                
        except Exception as e:
            print(f"❌ Penalty reset error: {e}")
            if self.db:
                self.db.rollback()
    
    def reset_to_normal_bandwidth(self, ip_address, username):
        """Reset bandwidth ke normal (10M/10M) - SIMULATION"""
        try:
            print(f"📡 [SIMULATION] Resetting {username} to normal bandwidth 10M/10M")
            
            # 🎯 TODO: Implement Mikrotik API reset di sini
            # self.apply_mikrotik_normal_bandwidth(ip_address, username)
            
            # Log reset action
            self.log_reset_action(username, ip_address)
            
            return True
            
        except Exception as e:
            print(f"❌ Reset bandwidth error: {e}")
            return False
    
    def apply_mikrotik_normal_bandwidth(self, ip_address, username):
        """Apply normal bandwidth ke Mikrotik - placeholder"""
        print(f"📡 [Mikrotik] Would reset {username} to 10M/10M")
        # TODO: Implement actual Mikrotik API call
        return True
    
    def log_reset_action(self, username, ip_address):
        """Log reset action"""
        try:
            with self.db.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO bandwidth_logs 
                    (username, ip_address, change_type, reason) 
                    VALUES (%s, %s, %s, %s)
                """, (username, ip_address, 'reset', 'Auto-reset after 10 minutes penalty'))
                
                self.db.commit()
                print(f"📝 Reset logged: {username} -> normal bandwidth")
                
        except Exception as e:
            print(f"❌ Reset logging error: {e}")
    
    def start_monitoring(self):
        """Start penalty reset monitoring"""
        print("🔧 Starting penalty reset monitor...")
        
        def monitor_loop():
            while True:
                try:
                    self.check_and_reset_penalties()
                    time.sleep(60)  # Check every 1 minute
                except Exception as e:
                    print(f"❌ Reset monitor error: {e}")
                    time.sleep(120)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        print("✅ Penalty reset monitor started")

# Integrasi ke main_system.py
def main():
    reset_manager = PenaltyResetManager()
    reset_manager.start_monitoring()
    
    try:
        while True:
            print("💚 Penalty reset monitor running... (10 minutes interval)")
            time.sleep(300)
    except KeyboardInterrupt:
        print("🛑 Stopping penalty reset monitor")

if __name__ == "__main__":
    main()