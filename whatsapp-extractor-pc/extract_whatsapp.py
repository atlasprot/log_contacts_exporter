#!/usr/bin/env python3
"""
WhatsApp Full Number Extractor
Extracts phone numbers from WhatsApp database via ADB
Requires: Rooted Android phone connected via USB
"""

import os
import re
import sqlite3
import subprocess
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
            print("⚠️ wa-crypt-tools not installed.")
            return None
        
        if db_file.exists():
            print("✅ Database decrypted!")
            return db_file
        return None
    
    def extract_from_whatsapp_db(self, db_path):
        """Extract ALL phone numbers from WhatsApp database"""
        print("\n📱 Extracting from WhatsApp...")
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # 1. WhatsApp Numbers/Contacts
            print("   [1/4] Reading WhatsApp contacts...")
            cursor.execute("SELECT jid FROM wa_contacts")
            for row in cursor.fetchall():
                jid = row[0]
                if jid:
                    phone = self.extract_phone_from_jid(jid)
                    if phone:
                        self.numbers[phone] = "WhatsApp Contact"
            
            # 2. Chat List (all conversations)
            print("   [2/4] Reading chat list...")
            cursor.execute("SELECT jid FROM chat")
            for row in cursor.fetchall():
                jid = row[0]
                if jid:
                    phone = self.extract_phone_from_jid(jid)
                    if phone:
                        if phone not in self.numbers:
                            self.numbers[phone] = "WhatsApp Chat"
            
            # 3. Messages - sender numbers
            print("   [3/4] Reading messages (sender numbers)...")
            cursor.execute("SELECT DISTINCT key_remote_jid FROM messages")
            for row in cursor.fetchall():
                jid = row[0]
                if jid:
                    phone = self.extract_phone_from_jid(jid)
                    if phone:
                        if phone not in self.numbers:
                            self.numbers[phone] = "WhatsApp Message"
            
            # 4. Numbers shared in message text
            print("   [4/4] Scanning messages for phone numbers...")
            cursor.execute("SELECT data FROM messages WHERE data IS NOT NULL")
            for row in cursor.fetchall():
                text = row[0]
                if text:
                    found_phones = self.find_phones_in_text(text)
                    for phone in found_phones:
                        if phone not in self.numbers:
                            self.numbers[phone] = "Phone in Message"
            
            conn.close()
            print(f"   Found {len(self.numbers)} phone numbers!")
            
        except Exception as e:
            print(f"❌ Error reading WhatsApp database: {e}")
    
    def find_phones_in_text(self, text):
        """Find phone numbers in message text"""
        phones = []
        # Iraqi formats
        patterns = [
            r'\+964[67]\d{9}',
            r'07\d{9}',
            r'01\d{9}',
            r'964[67]\d{9}',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                phone = match.group()
                phone = phone.replace("+", "").replace(" ", "")
                if phone.startswith("964"):
                    phone = "0" + phone[3:]
                if re.match(r'^0[67]\d{9}$', phone):
                    phones.append(phone)
        return phones
    
    def extract_phone_from_jid(self, jid):
        """Extract phone number from WhatsApp JID"""
        match = re.search(r'@', str(jid))
        if match:
            phone = jid[:match.start()]
            phone = phone.replace("+", "")
            if phone.startswith("964"):
                phone = "0" + phone[3:]
            if re.match(r'^0[67]\d{9}$', phone):
                return phone
        return None
    
    def export_to_csv(self, filename="whatsapp_numbers.csv"):
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
        print("📱 WhatsApp Full Number Extractor")
        print("=" * 50)
        
        # Check connection
        if not self.check_connection():
            return
        
        # Extract WhatsApp files
        if not self.extract_files():
            print("❌ Failed to extract WhatsApp files")
            return
        
        # Decrypt database
        db_path = self.decrypt_database()
        if not db_path:
            print("\n⚠️ Cannot decrypt database.")
            print("\n📋 Manual instructions:")
            print("1. Root your phone")
            print("2. Copy /data/data/com.whatsapp/databases/msgstore.db.crypt14 to /sdcard/")
            print("3. Copy /data/data/com.whatsapp/files/key to /sdcard/")
            print("4. Pull to computer and decrypt with wa-crypt-tools")
            return
        
        # Extract from WhatsApp
        self.extract_from_whatsapp_db(db_path)
        
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
