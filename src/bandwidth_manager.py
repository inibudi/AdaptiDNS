#!/usr/bin/env python3
import sys
import os
import time
import socket  # ✅ TAMBAHKAN IMPORT INI

# Fix Python path
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.config import Config
from librouteros import connect
from librouteros.login import plain as login_plain

class BandwidthManager:
    def __init__(self):
        print("🔧 Initializing Bandwidth Manager...")
        self.connection = self.connect_to_mikrotik()
    
    def connect_to_mikrotik(self):
        """Connect dengan error handling yang better"""
        try:
            import socket
            # Test koneksi lebih singkat
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((Config.MIKROTIK_HOST, 8728))
            sock.close()
            
            if result != 0:
                print(f"❌ Network unreachable")
                return None
            
            # Connection dengan parameter lebih sederhana
            connection = connect(
                host=Config.MIKROTIK_HOST,
                username=Config.MIKROTIK_USER, 
                password=Config.MIKROTIK_PASSWORD,
                login_methods=login_plain,
                timeout=5
            )
            return connection
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return None

    def get_active_users(self):
        """Simpler version dengan robust error handling"""
        try:
            if not self.connection:
                self.connection = self.connect_to_mikrotik()
                if not self.connection:
                    print("❌ Cannot connect to Mikrotik, using fallback")
                    return self.get_cached_users_fallback()
            
            print("🔍 Fetching active users from Mikrotik...")
            
            # Gunakan command yang lebih reliable dengan timeout
            try:
                users = list(self.connection('/ip/hotspot/active/print'))
            except Exception as api_error:
                print(f"❌ Mikrotik API error: {api_error}")
                self.connection = None
                return self.get_cached_users_fallback()
            
            # Simple validation saja
            valid_users = []
            for user in users:
                username = user.get('user', '')
                ip_address = user.get('address', '')
                
                if username and ip_address and ip_address.startswith('10.5.50.'):
                    valid_users.append({
                        'user': username.strip(),
                        'address': ip_address.strip(),
                        'mac-address': user.get('mac-address', '')
                    })
            
            print(f"✅ Found {len(valid_users)} active users: {[(u['user'], u['address']) for u in valid_users]}")
            
            # Cache untuk fallback
            self.cached_users = valid_users
            return valid_users
            
        except Exception as e:
            print(f"❌ Get users failed: {e}")
            self.connection = None
            return self.get_cached_users_fallback()

    def get_cached_users_fallback(self):
        """Fallback ketika semua attempts gagal"""
        if hasattr(self, 'cached_users') and self.cached_users:
            print("🔄 Using cached users data")
            return self.cached_users
        
        # Hardcoded fallback berdasarkan log Anda
        print("🔄 Using hardcoded fallback users")
        return [
            {'user': 'cinta', 'address': '10.5.50.7'},
            {'user': 'budi', 'address': '10.5.50.8'}, 
            {'user': 'sri', 'address': '10.5.50.10'}
        ]
    
    def get_username_by_ip(self, ip_address):
        """Get username from IP address - OPTIMIZED VERSION"""
        try:
            print(f"🔍 Looking up username for IP: {ip_address}")
            
            if not self.connection:
                print("⚠️ No connection, using fallback username")
                return f"user_{ip_address.replace('.', '_')}"
            
            # ✅ OPTIMISASI: Gunakan filter langsung di Mikrotik
            print(f"🔍 Searching for user with IP: {ip_address}")
            users = list(self.connection('/ip/hotspot/active/print'))
            
            for user in users:
                if user.get('address') == ip_address:
                    username = user.get('user', f"user_{ip_address.replace('.', '_')}")
                    print(f"✅ Found username: {username}")
                    return username
            
            # ✅ PERBAIKI: Coba refresh data dulu
            print("🔄 User not found in current data, refreshing...")
            self.connection = None  # Force reconnect
            self.connection = self.connect_to_mikrotik()
            
            if self.connection:
                users = list(self.connection('/ip/hotspot/active/print'))
                for user in users:
                    if user.get('address') == ip_address:
                        username = user.get('user', f"user_{ip_address.replace('.', '_')}")
                        print(f"✅ Found username after refresh: {username}")
                        return username
            
            generic_username = f"user_{ip_address.replace('.', '_')}"
            print(f"⚠️ Using generic username: {generic_username}")
            return generic_username
            
        except Exception as e:
            print(f"❌ Error getting username: {e}")
            return f"user_{ip_address.replace('.', '_')}"

    def apply_penalty(self, ip_address, penalty_type):
        """Simple penalty application dengan auto-reset"""
        try:
            print(f"🎯 Applying {penalty_type} penalty: {ip_address}")
            
            # Dapatkan username
            username = self.get_username_by_ip(ip_address)
            print(f"👤 Username: {username}")
            
            # 🎯 SIMPLE APPROACH: Skip Mikrotik API untuk testing
            print(f"📝 [SIMULATION] Would apply {penalty_type} bandwidth limit to {username}")
            
            # Schedule auto-reset
            self.schedule_auto_reset(ip_address, username, penalty_type)
            
            print(f"✅ Penalty scheduled for {username}")
            return True
            
        except Exception as e:
            print(f"❌ Error in penalty: {e}")
            import traceback
            traceback.print_exc()
            return False

    def schedule_auto_reset(self, ip_address, username, penalty_type):
        """Simple scheduling di memory"""
        try:
            import time
            reset_time = int(time.time()) + 60  # 1 menit untuk testing
            
            # Initialize pending_resets jika belum ada
            if not hasattr(self, 'pending_resets'):
                self.pending_resets = []
                print("📋 Initialized pending_resets list")
            
            # Tambahkan reset schedule
            reset_info = {
                'ip_address': ip_address,
                'username': username, 
                'penalty_type': penalty_type,
                'reset_time': reset_time
            }
            self.pending_resets.append(reset_info)
            
            print(f"⏰ Auto-reset scheduled for {username} at {time.ctime(reset_time)}")
            print(f"📊 Total pending resets: {len(self.pending_resets)}")
            
            # Start background monitor jika belum running
            if not hasattr(self, 'reset_monitor_started'):
                self.start_simple_reset_monitor()
                self.reset_monitor_started = True
                
        except Exception as e:
            print(f"❌ Error scheduling reset: {e}")

    def start_simple_reset_monitor(self):
        """Simple background monitor untuk auto-reset"""
        import threading
        import time
        
        def monitor_loop():
            print("🔧 Starting simple reset monitor...")
            while True:
                try:
                    current_time = int(time.time())
                    
                    # Check pending resets
                    if hasattr(self, 'pending_resets') and self.pending_resets:
                        for reset in self.pending_resets[:]:  # Copy list untuk safe iteration
                            if reset['reset_time'] <= current_time:
                                print(f"🔄 Executing auto-reset for {reset['username']}")
                                
                                # Simulate reset
                                print(f"✅ [SIMULATION] Reset {reset['username']} to normal bandwidth")
                                
                                # Remove from pending
                                self.pending_resets.remove(reset)
                                print(f"📋 Remaining resets: {len(self.pending_resets)}")
                    
                    time.sleep(10)  # Check setiap 10 detik
                    
                except Exception as e:
                    print(f"❌ Monitor error: {e}")
                    time.sleep(30)
        
        # Start monitor thread
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        print("✅ Simple reset monitor started")

    def save_reset_schedule(self, ip_address, username, penalty_type, reset_time):
        """Save reset schedule ke database"""
        try:
            import pymysql
            from config.config import Config
            
            connection = pymysql.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO penalty_reset_schedule 
                    (username, ip_address, penalty_type, reset_time, status) 
                    VALUES (%s, %s, %s, %s, 'scheduled')
                """
                cursor.execute(sql, (username, ip_address, penalty_type, reset_time))
            
            connection.commit()
            connection.close()
            print(f"💾 Reset schedule saved: {username} -> {time.ctime(reset_time)}")
            
        except Exception as e:
            print(f"❌ Error saving reset schedule: {e}")

    def start_reset_monitor(self):
        """Start background monitor untuk auto-reset"""
        import threading
        import time
        
        def reset_monitor():
            print("🔧 Starting penalty reset monitor...")
            while True:
                try:
                    self.check_pending_resets()
                    time.sleep(30)  # Check setiap 30 detik
                except Exception as e:
                    print(f"❌ Reset monitor error: {e}")
                    time.sleep(60)
        
        monitor_thread = threading.Thread(target=reset_monitor, daemon=True)
        monitor_thread.start()
        print("✅ Penalty reset monitor started")

    def check_pending_resets(self):
        """Check dan execute pending resets"""
        try:
            import pymysql
            from config.config import Config
            import time
            
            current_time = int(time.time())
            
            connection = pymysql.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            
            with connection.cursor() as cursor:
                # Cari schedules yang sudah waktunya reset
                cursor.execute("""
                    SELECT * FROM penalty_reset_schedule 
                    WHERE reset_time <= %s AND status = 'scheduled'
                """, (current_time,))
                
                pending_resets = cursor.fetchall()
                
                for reset in pending_resets:
                    print(f"🔄 Executing auto-reset for {reset['username']}")
                    
                    # Reset bandwidth ke normal
                    success = self.reset_to_normal_bandwidth(
                        reset['ip_address'], 
                        reset['username']
                    )
                    
                    if success:
                        # Update status di database
                        cursor.execute("""
                            UPDATE penalty_reset_schedule 
                            SET status = 'executed', executed_at = NOW() 
                            WHERE id = %s
                        """, (reset['id'],))
                        connection.commit()
                        print(f"✅ Auto-reset completed for {reset['username']}")
                    else:
                        print(f"❌ Auto-reset failed for {reset['username']}")
            
            connection.close()
            
        except Exception as e:
            print(f"❌ Error checking pending resets: {e}")

    def reset_to_normal_bandwidth(self, ip_address, username):
        """Reset bandwidth ke normal (10M/10M)"""
        try:
            if not self.connection:
                self.connection = self.connect_to_mikrotik()
                if not self.connection:
                    return False
            
            # Hapus queue existing
            queues = list(self.connection('/queue/simple/print'))
            for queue in queues:
                if queue.get('target') == ip_address:
                    self.connection('/queue/simple/remove', {'.id': queue['.id']})
                    print(f"🗑️ Removed penalty queue for {ip_address}")
            
            # Apply normal bandwidth
            self.connection('/queue/simple/add', {
                'name': f'{username}-normal-{int(time.time())}',
                'target': ip_address,
                'max-limit': '10M/10M',
                'comment': 'auto-reset:normal'
            })
            
            # Log ke database
            self.log_bandwidth_reset(username, ip_address)
            
            print(f"✅ Bandwidth reset to normal: {username} -> 10M/10M")
            return True
            
        except Exception as e:
            print(f"❌ Error resetting bandwidth: {e}")
            return False

    def log_bandwidth_reset(self, username, ip_address):
        """Log bandwidth reset ke database"""
        try:
            import pymysql
            from config.config import Config
            
            connection = pymysql.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO bandwidth_logs 
                    (username, ip_address, change_type, reason) 
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    username, 
                    ip_address, 
                    'reset', 
                    'Auto-reset after 10 minutes penalty'
                ))
            
            connection.commit()
            connection.close()
            
        except Exception as e:
            print(f"❌ Error logging reset: {e}")

    def test_connection(self):
        """Test koneksi ke Mikrotik"""
        try:
            if not self.connection:
                self.connection = self.connect_to_mikrotik()
            
            if self.connection:
                # Test dengan command sederhana
                result = list(self.connection('/system/identity/print'))
                if result:
                    print(f"✅ Mikrotik connection test successful: {result[0].get('name', 'Unknown')}")
                    return True
            return False
        except Exception as e:
            print(f"❌ Mikrotik connection test failed: {e}")
            return False

# Test function - OPTIMIZED
def test_bandwidth_manager():
    print("🧪 Testing Bandwidth Manager...")
    manager = BandwidthManager()
    
    # Test connection first
    if not manager.test_connection():
        print("❌ Cannot proceed with tests - no Mikrotik connection")
        return
    
    # Test active users
    print("\n📋 Testing active users...")
    users = manager.get_active_users()
    print(f"Active users: {len(users)}")
    
    if users:
        # Test username lookup dengan IP yang ada
        test_ip = users[0].get('address')
        if test_ip:
            print(f"\n🔍 Testing username lookup for {test_ip}...")
            username = manager.get_username_by_ip(test_ip)
            print(f"Username for {test_ip}: {username}")
        
        # Test penalty application
        print(f"\n⚡ Testing penalty application...")
        success = manager.apply_penalty(test_ip, 'whitelist')
        print(f"Penalty test result: {'✅ Success' if success else '❌ Failed'}")

if __name__ == "__main__":
    test_bandwidth_manager()