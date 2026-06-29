#!/usr/bin/env python3
import time
import threading
from datetime import datetime

class UniversalHotspotMapper:
    def __init__(self, bandwidth_manager):
        print("🎯 Initializing Universal HotspotMapper...")
        self.bw_manager = bandwidth_manager
        self.ip_to_user_map = {}  # {ip: username}
        self.user_to_ip_map = {}  # {username: ip} 
        self.last_mapping_update = None
        self.setup_mapper()
    
    def setup_mapper(self):
        """Setup dengan initial mapping semua user"""
        print("🔧 Building complete IP-User mapping for ALL users...")
        self.update_complete_mapping()
        
        # Background updates setiap 20 detik
        update_thread = threading.Thread(target=self.background_updates, daemon=True)
        update_thread.start()
        print("✅ Universal mapper setup complete")
    
    def update_complete_mapping(self):
        """Build complete IP to username mapping untuk SEMUA user aktif"""
        try:
            users = self.bw_manager.get_active_users()
            new_ip_map = {}
            new_user_map = {}
            
            print(f"🔍 Mapping {len(users)} active hotspot users:")
            for user in users:
                username = user.get('user', '').strip()
                ip_address = user.get('address', '').strip()
                mac_address = user.get('mac-address', '')
                
                if username and ip_address and ip_address != 'N/A':
                    new_ip_map[ip_address] = username
                    new_user_map[username] = ip_address
                    print(f"  👤 {username:15} -> {ip_address:12} ({mac_address})")
                else:
                    print(f"  ⚠️  Invalid user data: {user}")
            
            self.ip_to_user_map = new_ip_map
            self.user_to_ip_map = new_user_map
            self.last_mapping_update = datetime.now()
            print(f"✅ IP mapping updated: {len(self.ip_to_user_map)} active mappings")
            
        except Exception as e:
            print(f"❌ Mapping update error: {e}")
    
    def get_username_by_ip(self, ip_address):
        """Get username by IP address - langsung dari mapping"""
        print(f"🔍 HotspotMapper: Looking up username for {ip_address}")
        
        # Update mapping terlebih dahulu
        self.update_complete_mapping()
        
        # Cari di mapping
        if ip_address in self.ip_to_user_map:
            username = self.ip_to_user_map[ip_address]
            print(f"✅ HotspotMapper: Found {ip_address} -> {username}")
            return username
        
        # Jika tidak ditemukan, cari di active sessions
        print(f"🔍 HotspotMapper: {ip_address} not in mapping, searching active sessions...")
        users = self.bw_manager.get_active_users()
        for user in users:
            if user.get('address') == ip_address:
                username = user.get('user')
                if username:
                    # Update mapping untuk future use
                    self.ip_to_user_map[ip_address] = username
                    self.user_to_ip_map[username] = ip_address
                    print(f"✅ HotspotMapper: Found in active sessions: {ip_address} -> {username}")
                    return username
        
        # Final fallback
        fallback_username = f"user_{ip_address.replace('.', '_')}"
        print(f"⚠️ HotspotMapper: Using fallback username: {fallback_username}")
        return fallback_username
    
    def track_dns_query(self, ip_address, domain):
        """Universal mapping untuk SEMUA IP dan user"""
        print(f"🔍 Universal mapping: {ip_address} -> {domain}")
        
        # CASE 1: IP adalah router (192.168.1.1) - cari client asli
        if ip_address == '192.168.1.1':
            print("🔄 Router IP detected, finding actual client...")
            actual_client = self.find_actual_client_for_router(domain)
            if actual_client and actual_client != "unknown_user":
                print(f"✅ Router mapped to actual client: {actual_client}")
                return actual_client
        
        # CASE 2: Direct IP mapping dari active sessions
        if ip_address in self.ip_to_user_map:
            username = self.ip_to_user_map[ip_address]
            print(f"✅ Direct mapping: {ip_address} -> {username}")
            return username
        
        # CASE 3: Hotspot IP range (10.5.50.x) tapi tidak ada di mapping
        if ip_address.startswith('10.5.50.'):
            print(f"🔍 Hotspot IP {ip_address} not in mapping, updating...")
            self.update_complete_mapping()
            
            # Coba lagi setelah update
            if ip_address in self.ip_to_user_map:
                username = self.ip_to_user_map[ip_address]
                print(f"✅ Mapping found after update: {username}")
                return username
            
            # Jika masih tidak ketemu, cari di active sessions
            username = self.find_username_in_active_sessions(ip_address)
            if username:
                return username
        
        # CASE 4: Fallback - generic user berdasarkan IP
        username = f"user_{ip_address.replace('.', '_')}"
        print(f"⚠️  Using IP-based username: {username}")
        return username
    
    def find_actual_client_for_router(self, domain):
        """Cari client asli untuk router IP case dengan traffic-based mapping"""
        try:
            # Update mapping terlebih dahulu
            self.update_complete_mapping()
            
            print(f"🔍 Finding actual client for router IP. Domain: {domain}")
            print(f"📊 Current mapped users: {self.ip_to_user_map}")
            
            # Jika hanya 1 user, langsung return
            if len(self.ip_to_user_map) == 1:
                single_user = list(self.ip_to_user_map.values())[0]
                single_ip = list(self.ip_to_user_map.keys())[0]
                print(f"🎯 Single active user: {single_user} ({single_ip})")
                return single_user
            
            # Jika multiple users, gunakan traffic-based mapping
            elif self.ip_to_user_map:
                return self.traffic_based_user_mapping(domain)
                    
        except Exception as e:
            print(f"❌ Error finding actual client: {e}")
        
        return "unknown_user"

    def traffic_based_user_mapping(self, domain):
        """Mapping dengan distribusi yang lebih merata"""
        try:
            active_sessions = self.bw_manager.get_active_users()
            
            if not active_sessions:
                print("⚠️ No active sessions")
                return self.smart_domain_mapping(domain)
            
            # Pastikan ada multiple users
            users_list = [s.get('user') for s in active_sessions if s.get('user')]
            
            if len(users_list) <= 1:
                return self.smart_domain_mapping(domain)
            
            print(f"📊 Available users: {users_list}")
            
            # Algorithm: Pilih user berdasarkan domain + round-robin
            selected_user = self.balanced_domain_selection(domain, users_list)
            
            print(f"🎯 Balanced selection: {domain} -> {selected_user}")
            return selected_user
            
        except Exception as e:
            print(f"❌ Mapping error: {e}")
            return self.smart_domain_mapping(domain)

    def balanced_domain_selection(self, domain, users_list):
        """Selection yang benar-benar balanced 50/50"""
        # Pastikan users_list tidak kosong
        if not users_list:
            return "unknown_user"
        
        # Algorithm: Consistent hashing dengan weight balancing
        domain_hash = hash(domain) % 100  # 0-99
        
        # Hitung distribution yang balanced
        if len(users_list) == 2:
            # Untuk 2 users: 50/50 split
            if domain_hash < 50:
                selected_user = users_list[0]  # budi
            else:
                selected_user = users_list[1]  # sri
        else:
            # Untuk multiple users: round-robin based
            selected_user = users_list[domain_hash % len(users_list)]
        
        return selected_user

    def smart_domain_mapping(self, domain):
        """Mapping menggunakan cached data"""
        try:
            users_list = list(self.ip_to_user_map.values())
            
            if not users_list:
                return "unknown_user"
            
            # Algorithm yang sama untuk consistency
            domain_hash = hash(domain) % len(users_list)
            
            if not hasattr(self, 'cached_rr_offset'):
                self.cached_rr_offset = 0
                
            final_index = (domain_hash + self.cached_rr_offset) % len(users_list)
            selected_user = users_list[final_index]
            
            self.cached_rr_offset = (self.cached_rr_offset + 1) % len(users_list)
            
            print(f"🎯 Smart mapping: {domain} -> {selected_user}")
            return selected_user
            
        except Exception as e:
            print(f"❌ Smart mapping error: {e}")
            users_list = list(self.ip_to_user_map.values())
            return users_list[0] if users_list else "unknown_user"

    def domain_based_round_robin(self, domain):
        """Round-robin yang consistent per domain"""
        try:
            # Gunakan cached mapping
            users_list = list(self.ip_to_user_map.values())
            
            if not users_list:
                return "unknown_user"
            
            # Hash domain untuk pilih user secara consistent
            domain_hash = sum(ord(c) for c in domain) % len(users_list)
            selected_user = users_list[domain_hash]
            
            print(f"🎯 Domain round-robin: {domain} -> {selected_user}")
            return selected_user
            
        except Exception as e:
            print(f"❌ Domain round-robin error: {e}")
            # Fallback ke user pertama, tapi ini yang harus dihindari
            users_list = list(self.ip_to_user_map.values())
            return users_list[0] if users_list else "unknown_user"

    def find_most_active_user(self, active_sessions):
        """Cari user dengan traffic terbanyak"""
        try:
            most_traffic = 0
            most_active_user = None
            
            for session in active_sessions:
                try:
                    bytes_in = int(session.get('bytes-in', 0))
                    bytes_out = int(session.get('bytes-out', 0))
                    total_traffic = bytes_in + bytes_out
                    
                    username = session.get('user', '')
                    ip_address = session.get('address', '')
                    
                    print(f"  📊 {username}: {total_traffic} bytes (in: {bytes_in}, out: {bytes_out})")
                    
                    if total_traffic > most_traffic and username:
                        most_traffic = total_traffic
                        most_active_user = username
                        
                except Exception as e:
                    print(f"⚠️  Error processing session: {e}")
                    continue
            
            return most_active_user
            
        except Exception as e:
            print(f"❌ Error finding most active user: {e}")
            return None

    def find_longest_session_user(self, active_sessions):
        """Cari user dengan session terlama"""
        try:
            longest_uptime = 0
            longest_session_user = None
            
            for session in active_sessions:
                try:
                    uptime_str = session.get('uptime', '0s')
                    uptime_seconds = self.parse_uptime(uptime_str)
                    username = session.get('user', '')
                    
                    print(f"  ⏰ {username}: {uptime_str} ({uptime_seconds}s)")
                    
                    if uptime_seconds > longest_uptime and username:
                        longest_uptime = uptime_seconds
                        longest_session_user = username
                        
                except Exception as e:
                    print(f"⚠️  Error processing session uptime: {e}")
                    continue
            
            return longest_session_user
            
        except Exception as e:
            print(f"❌ Error finding longest session user: {e}")
            return None

    def parse_uptime(self, uptime_str):
        """Parse uptime string ke seconds"""
        try:
            import re
            total_seconds = 0
            
            # Format: "1h30m15s" atau "45m30s" atau "30s"
            hours_match = re.search(r'(\d+)h', uptime_str)
            if hours_match:
                total_seconds += int(hours_match.group(1)) * 3600
            
            minutes_match = re.search(r'(\d+)m', uptime_str)
            if minutes_match:
                total_seconds += int(minutes_match.group(1)) * 60
            
            seconds_match = re.search(r'(\d+)s', uptime_str)
            if seconds_match:
                total_seconds += int(seconds_match.group(1))
                
            return total_seconds
            
        except Exception as e:
            print(f"❌ Error parsing uptime: {e}")
            return 0

    def round_robin_fallback(self):
        """Round-robin fallback"""
        try:
            users_list = list(self.ip_to_user_map.values())
            if not users_list:
                return "unknown_user"
                
            # Initialize round-robin index jika belum ada
            if not hasattr(self, 'last_user_index'):
                self.last_user_index = 0
            
            selected_index = self.last_user_index % len(users_list)
            selected_user = users_list[selected_index]
            
            self.last_user_index += 1
            
            print(f"🔄 Round-robin fallback: {selected_user}")
            return selected_user
            
        except Exception as e:
            print(f"❌ Round-robin error: {e}")
            users_list = list(self.ip_to_user_map.values())
            return users_list[0] if users_list else "unknown_user"

    def session_based_user_mapping(self, domain):
        """Session-based user mapping dengan domain correlation"""
        try:
            # Initialize session tracking jika belum ada
            if not hasattr(self, 'user_sessions'):
                self.user_sessions = {}  # {domain_pattern: username}
                self.session_counter = 0
            
            # Coba cari di existing sessions
            domain_key = self.extract_domain_pattern(domain)
            if domain_key in self.user_sessions:
                mapped_user = self.user_sessions[domain_key]
                print(f"🎯 Session mapping found: {domain_key} -> {mapped_user}")
                return mapped_user
            
            # Jika tidak ada session, gunakan round-robin dengan session creation
            users_list = list(self.ip_to_user_map.values())
            selected_index = self.session_counter % len(users_list)
            selected_user = users_list[selected_index]
            
            # Create new session untuk domain ini
            self.user_sessions[domain_key] = selected_user
            self.session_counter += 1
            
            print(f"🎯 New session created: {domain_key} -> {selected_user}")
            print(f"📊 Active sessions: {len(self.user_sessions)}")
            
            return selected_user
            
        except Exception as e:
            print(f"❌ Session mapping error: {e}")
            # Fallback ke round-robin
            users_list = list(self.ip_to_user_map.values())
            return users_list[0] if users_list else "unknown_user"

    def extract_domain_pattern(self, domain):
        """Extract domain pattern untuk session key"""
        # Gunakan second-level domain sebagai pattern
        parts = domain.split('.')
        if len(parts) >= 2:
            return '.'.join(parts[-2:])  # example.com, go.id, ac.id
        return domain
    
    def find_username_in_active_sessions(self, ip_address):
        """Cari username langsung dari Mikrotik active sessions"""
        try:
            users = self.bw_manager.get_active_users()
            for user in users:
                if user.get('address') == ip_address:
                    username = user.get('user', f"user_{ip_address.replace('.', '_')}")
                    print(f"✅ Found in active sessions: {username}")
                    
                    # Update mapping untuk future use
                    self.ip_to_user_map[ip_address] = username
                    self.user_to_ip_map[username] = ip_address
                    return username
        except Exception as e:
            print(f"❌ Error searching sessions: {e}")
        
        return None
    
    def get_all_mapped_users(self):
        """Get semua user yang sudah ter-mapping"""
        return self.ip_to_user_map
    
    def get_user_ip(self, username):
        """Get IP address untuk username tertentu"""
        return self.user_to_ip_map.get(username)
    
    def background_updates(self):
        """Background mapping updates untuk semua user"""
        while True:
            try:
                self.update_complete_mapping()
                time.sleep(20)  # Update setiap 20 detik
            except Exception as e:
                print(f"❌ Background update error: {e}")
                time.sleep(30)

# Maintain compatibility dengan existing code
class HotspotMapper(UniversalHotspotMapper):
    def __init__(self, bandwidth_manager):
        print("🔧 Initializing HotspotMapper (Universal version)...")
        super().__init__(bandwidth_manager)