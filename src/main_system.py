#!/usr/bin/env python3
import sys
import os
import time
import threading

# FIX PYTHON PATH - Robust method
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.dns_parser.parser import DnsmasqLogParser
from app.penalty_engine import SimplePenaltyEngine
from app.penalty_reset import PenaltyResetManager  # 🆕 IMPORT BARU
from config.config import Config

class BandwidthPenaltySystem:
    def __init__(self):
        print("🚀 Initializing Bandwidth Penalty System...")
        
        # Initialize components
        self.dns_parser = DnsmasqLogParser()
        self.penalty_engine = SimplePenaltyEngine()
        self.reset_manager = PenaltyResetManager()  # 🆕 RESET MANAGER
        
        print("✅ System initialized successfully!")
    
    def start_monitoring(self):
        """Start semua monitoring services"""
        print("🎯 Starting all monitoring services...")
        
        # 1. Start DNS log monitoring
        print("📡 Starting DNS log monitoring...")
        self.dns_parser.start_monitoring()
        
        # 2. Start penalty engine
        print("⚡ Starting penalty engine...")
        self.penalty_engine.start_monitoring()
        
        # 3. 🆕 START PENALTY RESET MONITOR
        print("🔄 Starting penalty reset monitor...")
        self.reset_manager.start_monitoring()
        
        # Main loop
        try:
            while True:
                print("💚 System running normally... (Press Ctrl+C to stop)")
                time.sleep(30)
        except KeyboardInterrupt:
            print("🛑 System stopped by user")

def main():
    try:
        print("=" * 50)
        print("🚀 BANDWIDTH PENALTY SYSTEM WITH AUTO-RESET")
        print("=" * 50)
        
        system = BandwidthPenaltySystem()
        system.start_monitoring()
        
    except Exception as e:
        print(f"💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()