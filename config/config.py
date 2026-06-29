import os

class Config:
    # Database Configuration
    DB_HOST = 'localhost'
    DB_USER = 'bandwidth_user'
    DB_PASSWORD = 'secure_password_123'  # Ganti dengan password MySQL
    DB_NAME = 'bandwidth_monitorsp'
    
    # Mikrotik Configuration
    MIKROTIK_HOST = '192.168.1.1'
    MIKROTIK_USER = 'admin'
    MIKROTIK_PASSWORD = 'your_strong_password'  # Ganti dengan password Mikrotik
    
    # Application Configuration
    API_HOST = '192.168.1.253'
    API_PORT = 5001
    
    # ML Model Paths
    MODEL_TFIDF_PATH = '/opt/bandwidth-monitor/models/Data_TFIDF.pkl'
    MODEL_SVC_PATH = '/opt/bandwidth-monitor/models/SVC.pkl'
    
    # Logging
    LOG_LEVEL = 'INFO'
    
    # Penalty Rules
    PENALTY_RULES = {
        'porno': '5M/5M',
        'judi': '7M/7M',  
        'penipuan': '9M/9M',
        'whitelist': '10M/10M'
    }