#!/usr/bin/env python3
"""
WhatsApp Number Extractor + Call History
Extracts phone numbers from WhatsApp database and call history via ADB
Requires: Rooted Android phone connected via USB
"""

import os
import re
import sqlite3
import subprocess
import sys
import csv
from pathlib import Path

class WhatsAppExtractor:
    def __init__(self):
        self.numbers = {}
        self.temp_dir = Path("temp_whatsapp")
        self.temp_dir.mkdir(exist_ok=True)
    
    def run_adb(self, command):
        """Run ADB command"""
        result = subprocess.run(
            ["adb"] + command.split(),
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr
    
    def check_connection(self):
        """Check if phone is connected"""
        stdout, _ = self.run_adb("devices")
        devices = [line for line in stdout.split("\n") if "device" in line and "List" not in line]
        if not devices:
            print("❌ No device connected. Connect your phone via USB and enable USB debugging.")
            return False
        print(f"✅ Phone connected: {devices[0]}")
        return True
    
    def clean_phone(self, phone):
        """Clean and normalize phone number"""
        if not phone:
            return None
        # Remove spaces, dashes, etc.
        phone = re.sub(r'[\s\-\(\)]', '', phone)
        # Remove + prefix
        phone = phone.replace("+", "")
        # Convert 964 to 0
        if phone.startswith("964"):
            phone = "0" + phone[3:]
        return phone
    
    def is_valid_phone(self, phone):
        """Check if phone is valid Iraqi format"""
        return bool(re.match(r'^0[67]\d{9}$', phone))
    
    def extract_files(self):
        """Extract WhatsApp database files from phone"""
        print("\n📁 Extracting WhatsApp files...")
        
        # Create directories on phone
        self.run_adb("shell su -c 'mkdir -p /sdcard/whatsapp_extract'")
        
        # Copy encrypted database
        print("   Copying msgstore.db.crypt14...")
        self.run_adb(f"shell su -c 'cp /data/data/com.whatsapp/databases/msgstore.db.crypt14 /sdcard/whatsapp_extract/'")
        
        # Copy key file (if exists)
        print("   Copying key file...")
        self.run_adb(f"shell su -c 'cp /data/data/com.whatsapp/files/key /sdcard/whatsapp_extract/' 2>/dev/null || echo 'Key not found'")
        
        # Pull to computer
        print("   Pulling files to computer...")
        self.run_adb(f"pull /sdcard/whatsapp_extract {self.temp_dir}")
        
        return (self.temp_dir / "msgstore.db.crypt14").exists()
    
    def decrypt_database(self):
        """Decrypt the WhatsApp database"""
        crypt_file = self.temp_dir / "msgstore.db.crypt14"
        key_file = self.temp_dir / "key"
        db_file = self.temp_dir / "msgstore.db"
        
        print("\n🔓 Decrypting database...")
        
        if not crypt_file.exists():
            print("❌ Encrypted database not found!")
            return None
        
        # Try wa-crypt-tools decryption
        try:
            import wa_crypt
            print("   Using wa-crypt-tools...")
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    key = f.read()
                wa_crypt.decrypt_file(str(crypt_file), str(db_file), key)
            else:
                print("❌ Key file not found. Cannot decrypt database.")
                return None
        except ImportError:
            print("⚠️ wa-crypt-tools not installed. Trying alternative methods...")
            return None
        
        if db_file.exists():
            print("✅ Database decrypted!")
            return db_file
        return None
    
    def extract_numbers_from_db(self, db_path):
        """Extract phone numbers from WhatsApp database"""
        print("\n📱 Extracting WhatsApp numbers...")
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Get phone numbers from chat table
            print("   Reading chats...")
            cursor.execute("SELECT DISTINCT jid FROM chat")
            for row in cursor.fetchall():
                jid = row[0]
                if jid:
                    phone = self.extract_phone_from_jid(jid)
                    if phone and phone not in self.numbers:
                        self.numbers[phone] = "WhatsApp"
            
            # Get phone numbers from messages
            print("   Reading messages...")
            cursor.execute("SELECT DISTINCT key_remote_jid FROM messages")
            for row in cursor.fetchall():
                jid = row[0]
                if jid:
                    phone = self.extract_phone_from_jid(jid)
                    if phone and phone not in self.numbers:
                        self.numbers[phone] = "WhatsApp"
            
            # Get phone numbers from group participants
            print("   Reading group members...")
            cursor.execute("SELECT DISTINCT jid FROM group_participants")
            for row in cursor.fetchall():
                jid = row[0]
                if jid:
                    phone = self.extract_phone_from_jid(jid)
                    if phone and phone not in self.numbers:
                        self.numbers[phone] = "WhatsApp"
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Error reading WhatsApp database: {e}")
    
    def extract_calls(self):
        """Extract phone numbers from call history via ADB"""
        print("\n📞 Extracting call history...")
        
        # Try content provider method (no root needed for call log)
        print("   Querying call log...")
        stdout, _ = self.run_adb("shell content query --uri content://call_log/calls --projection number,duration")
        
        call_count = 0
        for line in stdout.split("\n"):
            if "number=" in line:
                match = re.search(r'number=([^\s,]+)', line)
                if match:
                    phone = self.clean_phone(match.group(1))
                    if phone and self.is_valid_phone(phone):
                        if phone not in self.numbers:
                            self.numbers[phone] = "Call Log"
                            call_count += 1
        
        # Try database method if content provider didn't work
        if call_count == 0:
            print("   Trying database method...")
            self.run_adb("shell su -c 'mkdir -p /sdcard/calls_extract'")
            self.run_adb("shell su -c 'cp /data/data/com.android.providers.telephony/databases/telephony.db /sdcard/calls_extract/' 2>/dev/null || echo 'Not found'")
            self.run_adb("pull /sdcard/calls_extract temp_calls.db 2>/dev/null")
            
            calls_db = Path("temp_calls.db")
            if calls_db.exists():
                try:
                    conn = sqlite3.connect(str(calls_db))
                    cursor = conn.cursor()
                    cursor.execute("SELECT DISTINCT number FROM calls")
                    for row in cursor.fetchall():
                        phone = self.clean_phone(row[0])
                        if phone and self.is_valid_phone(phone):
                            if phone not in self.numbers:
                                self.numbers[phone] = "Call Log"
                                call_count += 1
                    conn.close()
                    calls_db.unlink()
                except Exception as e:
                    print(f"   ⚠️ Error: {e}")
        
        print(f"   Extracted {call_count} call numbers")
    
    def extract_phone_from_jid(self, jid):
        """Extract phone number from WhatsApp JID"""
        match = re.search(r'@', jid)
        if match:
            phone = jid[:match.start()]
            phone = phone.replace("+", "")
            if phone.startswith("964"):
                phone = "0" + phone[3:]
            if re.match(r'^0[67]\d{9}$', phone):
                return phone
        return None
    
    def export_to_csv(self, filename="all_numbers.csv"):
        """Export numbers to CSV"""
        print(f"\n💾 Exporting to {filename}...")
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["phone", "source"])
            for phone, source in sorted(self.numbers.items()):
                writer.writerow([phone, source])
        
        print(f"✅ Exported {len(self.numbers)} numbers to {filename}")
    
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            print("\n🧹 Cleaned up temporary files")
    
    def run(self):
        """Main execution"""
        print("=" * 50)
        print("📱 WhatsApp + Call History Extractor")
        print("=" * 50)
        
        # Check connection
        if not self.check_connection():
            return
        
        # Extract call history (always)
        self.extract_calls()
        
        # Extract WhatsApp (requires root + decryption)
        if self.extract_files():
            db_path = self.decrypt_database()
            if db_path:
                self.extract_numbers_from_db(db_path)
        
        if not self.numbers:
            print("\n⚠️ No phone numbers found")
            return
        
        # Export
        self.export_to_csv()
        
        # Cleanup
        self.cleanup()
        
        print("\n" + "=" * 50)
        print(f"✅ Done! Found {len(self.numbers)} numbers")
        print("=" * 50)

if __name__ == "__main__":
    extractor = WhatsAppExtractor()
    extractor.run()
