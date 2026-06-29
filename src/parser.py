#!/usr/bin/env python3
import sys
import os
import re
import time
import pymysql
import pickle
from datetime import datetime
from config.config import Config
import threading

class UniversalDnsmasqParser:
    def __init__(self):
        self.log_file = "/var/log/dnsmasq.log"
        self.last_position = 0
        self.setup_database()
        self.load_ml_models()
        self.setup_bandwidth_manager()
    
    def setup_bandwidth_manager(self):
        """Setup universal bandwidth manager"""
        try:
            from app.mikrotik.bandwidth_manager import BandwidthManager
            from app.mikrotik.hotspot_mapper import UniversalHotspotMapper
            self.bw_manager = BandwidthManager()
            self.hotspot_mapper = UniversalHotspotMapper(self.bw_manager)
            print("✅ Universal bandwidth manager integrated")
        except Exception as e:
            print(f"❌ Bandwidth manager setup failed: {e}")
            self.bw_manager = None
            self.hotspot_mapper = None
    
    def load_ml_models(self):
        """Load ML models untuk integrated classification"""
        try:
            with open(Config.MODEL_TFIDF_PATH, 'rb') as f:
                self.tfidf = pickle.load(f)
            with open(Config.MODEL_SVC_PATH, 'rb') as f:
                self.svc_model = pickle.load(f)
            print("✅ ML models loaded in parser")
        except Exception as e:
            print(f"❌ ML models loading failed: {e}")
            self.tfidf = None
            self.svc_model = None
    
    def setup_database(self):
        """Setup database connection"""
        try:
            self.connection = pymysql.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            print("✅ Parser database connected")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            self.connection = None
    
    def extract_actual_client_ip(self, detected_ip, raw_line):
        """Extract client IP asli dari reverse DNS lookup"""
        
        # CASE 1: Reverse DNS lookup untuk hotspot clients
        reverse_pattern = r'query\[PTR\]\s+(\d+)\.50\.5\.10\.in-addr\.arpa\s+from\s+192\.168\.1\.1'
        match = re.search(reverse_pattern, raw_line)
        if match:
            client_id = match.group(1)
            actual_ip = f"10.5.50.{client_id}"
            print(f"🎯 EXTRACTED Hotspot IP from reverse DNS: {actual_ip}")
            return actual_ip
        
        # CASE 2: Jika IP adalah router, gunakan traffic-based mapping
        if detected_ip == '192.168.1.1':
            if self.hotspot_mapper:
                # Dapatkan username dari traffic-based mapping
                username = self.hotspot_mapper.track_dns_query(detected_ip, "temp-domain")
                
                # Cari IP dari username yang terpilih
                mapped_users = self.hotspot_mapper.get_all_mapped_users()
                user_ip = self.hotspot_mapper.get_user_ip(username)
                
                if user_ip:
                    print(f"🎯 Traffic-based mapping: {username} -> {user_ip}")
                    return user_ip
        
        return detected_ip  # Fallback ke IP yang terdeteksi
    
    def classify_domain(self, domain):
        """Enhanced classification dengan rule-based fallback"""
        
        # 🎯 RULE-BASED PRE-CLASSIFICATION (priority)
        rule_based_result = self.rule_based_pre_classification(domain)
        if rule_based_result:
            return rule_based_result
        
        # ML Classification
        ml_result = self.ml_classification(domain)
        if ml_result:
            return ml_result
        
        # Final fallback
        return 'whitelist', 0.80

    def rule_based_pre_classification(self, domain):
        """Rule-based classification dengan patterns yang jelas"""
        domain_lower = domain.lower()
        
        # 🎯 JUDI PATTERNS (high confidence)
        judi_patterns = [
            'poker', 'casino', 'judi', 'slot', 'betting', 'gambling', 'taruhan',
            'togel', 'sbobet', 'maxbet', 'bola', 'toto', 'qq', 'domino'
        ]
        for pattern in judi_patterns:
            if pattern in domain_lower:
                print(f"🎯 Rule-based JUDI: {domain} -> judi")
                return 'judi', 0.95
        
        # 🎯 PENIPUAN PATTERNS (high confidence)
        scam_patterns = [
            'scam', 'phishing', 'fraud', 'penipu', 'fake', 'klik', 'hadiah',
            'undian', 'giveaway', 'lotre', 'duit', 'uang', 'reward'
        ]
        for pattern in scam_patterns:
            if pattern in domain_lower:
                print(f"🎯 Rule-based PENIPUAN: {domain} -> penipuan")
                return 'penipuan', 0.90
        
        # 🎯 PORNO PATTERNS (high confidence)
        porno_patterns = [
            'porno', 'xxx', 'sex', 'adult', 'bokep', 'mesum', 'dewasa',
            'hot', 'nude', 'erotic', 'fuck', 'ass', 'tits'
        ]
        for pattern in porno_patterns:
            if pattern in domain_lower:
                print(f"🎯 Rule-based PORNO: {domain} -> porno")
                return 'porno', 0.97
        
        # 🎯 WHITELIST PATTERNS (high confidence)
        whitelist_patterns = [
            'google', 'youtube', 'github', 'stackoverflow', 'wikipedia',
            'kemdikbud', 'go.id', 'ac.id', 'sch.id', 'edu.', 'school'
        ]
        for pattern in whitelist_patterns:
            if pattern in domain_lower:
                print(f"🎯 Rule-based WHITELIST: {domain} -> whitelist")
                return 'whitelist', 0.98
        
        return None

    def ml_classification(self, domain):
        """ML classification dengan confidence threshold"""
        try:
            if not self.tfidf or not self.svc_model:
                return None
            
            domain_clean = self.preprocess_domain(domain)
            domain_tfidf = self.tfidf.transform([domain_clean])
            
            prediction = self.svc_model.predict(domain_tfidf)[0]
            probabilities = self.svc_model.predict_proba(domain_tfidf)[0]
            confidence = max(probabilities)
            
            # Confidence threshold
            if confidence < 0.80:  # Increased threshold
                print(f"⚠️  Low ML confidence ({confidence:.2f}): {domain}")
                return None
            
            print(f"🎯 ML Classification: {domain} -> {prediction} ({confidence:.2f})")
            return prediction, confidence
            
        except Exception as e:
            print(f"❌ ML classification failed: {e}")
            return None
    
    def preprocess_domain(self, domain):
        """Preprocessing domain"""
        import re
        domain = re.sub(r'https?://(www\.)?', '', domain)
        domain = domain.split('/')[0]
        domain = domain.split('?')[0]
        return domain.strip().lower()
    
    def rule_based_classification(self, domain):
        """Rule-based classification fallback"""
        domain_lower = domain.lower()
        if 'judi' in domain_lower or 'poker' in domain_lower or 'casino' in domain_lower:
            return 'judi', 0.95
        elif 'porno' in domain_lower or 'xxx' in domain_lower or 'sex' in domain_lower:
            return 'porno', 0.90
        elif 'scam' in domain_lower or 'phishing' in domain_lower or 'fraud' in domain_lower:
            return 'penipuan', 0.85
        else:
            return 'whitelist', 0.80
    
    def get_username_from_ip(self, ip_address, domain):
        """Universal username mapping untuk SEMUA user"""
        try:
            if self.hotspot_mapper:
                username = self.hotspot_mapper.track_dns_query(ip_address, domain)
                return username
        except Exception as e:
            print(f"❌ Username mapping failed: {e}")
        
        # Fallback mapping berdasarkan IP pattern
        if ip_address == '192.168.1.1':
            return "hotspot_user"
        elif ip_address.startswith('10.5.50.'):
            return f"hotspot_{ip_address.replace('.', '_')}"
        else:
            return f"user_{ip_address.replace('.', '_')}"
    
    def parse_log_line(self, line):
        """Original parsing method"""
        print(f"📝 Raw log: {line.strip()}")
        
        patterns = [
            r'query\[(A|AAAA)\]\s+([\w\.-]+)\s+from\s+(\d+\.\d+\.\d+\.\d+)',
            r'([\w\.-]+)\s+is\s+[^\s]+\s+from\s+(\d+\.\d+\.\d+\.\d+)',
            r'forwarded\s+([\w\.-]+)\s+to\s+.*from\s+(\d+\.\d+\.\d+\.\d+)'
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, line)
            if match:
                print(f"✅ Pattern {i+1} matched: {match.groups()}")
                
                if i == 0:  # Standard query
                    domain = match.group(2)
                    client_ip = match.group(3)
                elif i == 1:  # Cached response
                    domain = match.group(1)
                    client_ip = match.group(2)
                elif i == 2:  # Forwarded query
                    domain = match.group(1)
                    client_ip = match.group(2)
                
                # Skip server IP
                if client_ip in ['127.0.0.1', '192.168.1.253']:
                    print(f"⏭️ Skipping server IP: {client_ip}")
                    return None
                
                # Extract actual client IP jika router IP
                actual_ip = self.extract_actual_client_ip(client_ip, line)
                print(f"🎯 Processing: {actual_ip} -> {domain} (original: {client_ip})")
                
                # Integrated processing
                classification, confidence = self.classify_domain(domain)
                username = self.get_username_from_ip(actual_ip, domain)
                
                print(f"👤 Username: {username}")
                print(f"🏷️ Classification: {classification} ({confidence:.2f})")
                
                return {
                    'type': 'query',
                    'timestamp': datetime.now(),
                    'client_ip': actual_ip,
                    'domain': domain,
                    'username': username,
                    'classification': classification,
                    'confidence': confidence,
                    'status': 'processed',
                    'raw_line': line.strip()
                }
        
        return None
    
    def save_to_database(self, log_data):
        """Save ke database dengan data lengkap - ROBUST VERSION"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print(f"💾 Attempting save (attempt {retry_count + 1}): {log_data['username']} -> {log_data['domain']}")
                
                # Ensure connection is alive
                try:
                    if self.connection:
                        self.connection.ping(reconnect=True)
                    else:
                        print("🔄 No database connection, reconnecting...")
                        self.setup_database()
                except Exception as conn_error:
                    print(f"🔄 Connection ping failed: {conn_error}")
                    self.setup_database()
                
                if not self.connection:
                    print("❌ No database connection available")
                    return False
                
                with self.connection.cursor() as cursor:
                    sql = """
                        INSERT INTO user_access 
                        (username, ip_address, domain, access_time, classification, confidence, status) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    cursor.execute(sql, (
                        log_data['username'],
                        log_data['client_ip'],
                        log_data['domain'],
                        log_data['timestamp'],
                        log_data['classification'],
                        log_data['confidence'],
                        log_data['status']
                    ))
                
                self.connection.commit()
                print(f"✅ SUCCESS: Saved to database - {log_data['username']} -> {log_data['domain']} -> {log_data['classification']}")
                return True
                
            except Exception as e:
                retry_count += 1
                print(f"❌ Database save error (attempt {retry_count}): {e}")
                
                if retry_count < max_retries:
                    print("🔄 Retrying...")
                    time.sleep(1)
                    try:
                        self.setup_database()  # Full reconnect
                    except Exception as reconnect_error:
                        print(f"❌ Reconnect failed: {reconnect_error}")
                else:
                    print("💥 MAX RETRIES REACHED: Failed to save data")
                    return False
        
        return False
    
    def tail_log(self):
        """Tail log file dengan integrated processing"""
        try:
            if not os.path.exists(self.log_file):
                print(f"❌ Log file not found: {self.log_file}")
                open(self.log_file, 'a').close()
                print(f"✅ Created log file: {self.log_file}")
            
            print(f"📁 Monitoring log file: {self.log_file}")
            
            with open(self.log_file, 'r') as file:
                file.seek(0, 2)  # Ke akhir file
                
                while True:
                    line = file.readline()
                    if not line:
                        time.sleep(0.1)
                        continue
                    
                    parsed_data = self.parse_log_line(line)
                    if parsed_data:
                        success = self.save_to_database(parsed_data)
                        if not success:
                            print("💥 CRITICAL: Failed to save parsed data to database")
                        
        except Exception as e:
            print(f"❌ Log tailing error: {e}")
            time.sleep(5)
    
    def start_monitoring(self):
        """Start monitoring"""
        print("🚀 Starting UNIVERSAL DNS monitoring with integrated processing...")
        monitor_thread = threading.Thread(target=self.tail_log, daemon=True)
        monitor_thread.start()
        print("✅ Universal DNS monitoring started")

# Enhanced version dengan manual mapping
class DnsmasqLogParser(UniversalDnsmasqParser):
    def __init__(self):
        print("🔧 Initializing DnsmasqLogParser (Enhanced version)...")
        super().__init__()
    
    def get_username_from_ip(self, ip_address, domain):
        """Get username from IP dengan prioritas mapping real-time"""
        
        # 1. Coba dari hotspot mapper terlebih dahulu
        try:
            if self.hotspot_mapper:
                username = self.hotspot_mapper.get_username_by_ip(ip_address)
                if username and username != f"user_{ip_address.replace('.', '_')}":
                    print(f"✅ Hotspot mapper found: {ip_address} -> {username}")
                    return username
        except Exception as e:
            print(f"⚠️ Hotspot mapper error: {e}")
        
        # 2. Manual mapping berdasarkan data aktual
        manual_mapping = {
            '10.5.50.8': 'budi'  # Hanya budi yang aktif
        }
        
        if ip_address in manual_mapping:
            username = manual_mapping[ip_address]
            print(f"✅ Manual mapping: {ip_address} -> {username}")
            return username
        
        # 3. Final fallback
        username = f"user_{ip_address.replace('.', '_')}"
        print(f"⚠️ Using fallback username: {username}")
        return username
    
    def parse_log_line(self, line):
        """OVERRIDE: Enhanced parsing dengan actual client detection"""
        print(f"📝 Raw log: {line.strip()}")
        
        # 🎯 DETECT CLIENT IP DARI BERBAGAI PATTERN
        client_ip = self.extract_client_ip_from_patterns(line)
        
        if client_ip:
            # 🎯 EXTRACT DOMAIN 
            domain = self.extract_domain_from_line(line)
            print(f"🔍 Extracted domain: {domain}")
            
            if not domain:
                print("❌ No domain extracted")
                return None
            
            # 🎯 GET USERNAME FROM CLIENT IP (gunakan override method)
            username = self.get_username_from_ip(client_ip, domain)
            
            # 🎯 CLASSIFY DOMAIN
            classification, confidence = self.classify_domain(domain)
            print(f"🔍 Classification result: {classification} (confidence: {confidence})")
            
            parsed_data = {
                'type': 'query',
                'timestamp': datetime.now(),
                'client_ip': client_ip,
                'domain': domain,
                'username': username,
                'classification': classification,
                'confidence': confidence,
                'status': 'processed',
                'raw_line': line.strip()
            }
            
            print(f"🎯 ENHANCED MAPPING: {client_ip} -> {username} -> {domain} -> {classification}")
            return parsed_data
        else:
            # Fallback ke parent class parsing
            print("⚠️  No client IP detected, using parent parsing")
            return super().parse_log_line(line)
    
    def extract_client_ip_from_patterns(self, line):
        """Extract client IP yang AKURAT - FIXED VERSION"""
        
        # PATTERN 1: Reverse DNS lookup (paling akurat untuk hotspot)
        reverse_pattern = r'query\[PTR\]\s+(\d+)\.50\.5\.10\.in-addr\.arpa\s+from\s+192\.168\.1\.1'
        match = re.search(reverse_pattern, line)
        if match:
            client_id = match.group(1)
            actual_ip = f"10.5.50.{client_id}"
            print(f"🎯 Reverse DNS detected: {actual_ip}")
            return actual_ip
        
        # PATTERN 2: Direct client query dari hotspot
        direct_pattern = r'query\[[A]+\]\s+([\w\.-]+)\s+from\s+(10\.5\.50\.\d+)'
        match = re.search(direct_pattern, line)
        if match:
            client_ip = match.group(2)
            print(f"🎯 Direct hotspot client: {client_ip}")
            return client_ip
        
        # PATTERN 3: Query dari router - GUNAKAN ACTIVE USER MAPPING
        router_pattern = r'query\[(A|AAAA|HTTPS)\]\s+([\w\.-]+)\s+from\s+192\.168\.1\.1'
        match = re.search(router_pattern, line)
        if match:
            domain = match.group(2)
            print(f"🎯 Router query: {domain}")
            
            # 🎯 FIX: Gunakan ACTIVE USER dari hotspot mapper, bukan domain-based
            if self.hotspot_mapper:
                active_users = self.hotspot_mapper.get_all_mapped_users()
                print(f"📊 Active users: {active_users}")
                
                # Jika hanya ada 1 user aktif, gunakan IP tersebut
                if len(active_users) == 1:
                    actual_ip = list(active_users.keys())[0]
                    print(f"🎯 Single active user detected: {actual_ip}")
                    return actual_ip
                elif active_users:
                    # Untuk multiple users, pilih berdasarkan round-robin sederhana
                    ips = list(active_users.keys())
                    if not hasattr(self, 'last_ip_index'):
                        self.last_ip_index = 0
                    
                    selected_ip = ips[self.last_ip_index % len(ips)]
                    self.last_ip_index += 1
                    print(f"🎯 Multiple users, selected: {selected_ip}")
                    return selected_ip
            
            # Fallback: Gunakan IP dari user yang paling mungkin (budi)
            print("🎯 Using default IP: 10.5.50.8")
            return "10.5.50.8"
        
        print("⚠️ No client IP detected in log line")
        return None

    def extract_domain_from_line(self, line):
        """Extract domain dari berbagai pattern - FIXED VERSION"""
        patterns = [
            r'query\[(A|AAAA|HTTPS)\]\s+([\w\.-]+)\s+from',  # Standard query
            r'forwarded\s+([\w\.-]+)\s+to',                  # Forwarded query  
            r'cached\s+([\w\.-]+)\s+is',                     # Cached response
            r'([\w\.-]+)\s+is\s+[^\s]+\s+from'               # Reply with data
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                # Tentukan group mana yang berisi domain
                if len(match.groups()) == 2:
                    domain = match.group(2)  # Pattern dengan 2 groups
                else:
                    domain = match.group(1)  # Pattern dengan 1 group
                    
                if domain and not domain.endswith('.arpa'):
                    print(f"✅ Domain extracted: {domain} (pattern: {pattern})")
                    return domain
        
        print(f"❌ No domain pattern matched in line: {line.strip()}")
        return None