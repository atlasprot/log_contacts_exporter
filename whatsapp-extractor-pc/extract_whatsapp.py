#!/usr/bin/env python3
"""
WhatsApp Number Extractor
Extracts phone numbers from WhatsApp database via ADB
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
            # Check if wa-crypt-tools is installed
            import wa_crypt
            print("   Using wa-crypt-tools...")
            # Decrypt using the key
            if key_file.exists():
                # Read key file
                with open(key_file, 'rb') as f:
                    key = f.read()
                # Decrypt
                wa_crypt.decrypt_file(str(crypt_file), str(db_file), key)
            else:
                print("❌ Key file not found. Cannot decrypt database.")
                print("   The database is encrypted and requires the WhatsApp key.")
                return None
        except ImportError:
            print("⚠️ wa-crypt-tools not installed. Trying alternative methods...")
            # Fallback: try common key locations
            return None
        
        if db_file.exists():
            print("✅ Database decrypted!")
            return db_file
        return None
    
    def extract_numbers_from_db(self, db_path):
        """Extract phone numbers from WhatsApp database"""
        print("\n📱 Extracting phone numbers...")
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Get phone numbers from chat table (jid field)
            print("   Reading chats...")
            cursor.execute("SELECT DISTINCT jid FROM chat")
            for row in cursor.fetchall():
                jid = row[0]
                if jid:
                    phone = self.extract_phone_from_jid(jid)
                    if phone and phone not in self.numbers:
                        self.numbers[phone] = ""
            
            # Get phone numbers from messages (key_remote_jid)
            print("   Reading messages...")
            cursor.execute("SELECT DISTINCT key_remote_jid FROM messages")
            for row in cursor.fetchall():
                jid = row[0]
                if jid:
                    phone = self.extract_phone_from_jid(jid)
                    if phone and phone not in self.numbers:
                        self.numbers[phone] = ""
            
            # Get phone numbers from group participants
            print("   Reading group members...")
            cursor.execute("SELECT DISTINCT jid FROM group_participants")
            for row in cursor.fetchall():
                jid = row[0]
                if jid:
                    phone = self.extract_phone_from_jid(jid)
                    if phone and phone not in self.numbers:
                        self.numbers[phone] = ""
            
            conn.close()
            print(f"   Found {len(self.numbers)} unique phone numbers!")
            
        except Exception as e:
            print(f"❌ Error reading database: {e}")
        
        return self.numbers
    
    def extract_phone_from_jid(self, jid):
        """Extract phone number from WhatsApp JID"""
        # JID format: 07XXXXXXXX@s.whatsapp.net or 964XXXXXXXXX@s.whatsapp.net
        match = re.search(r'@', jid)
        if match:
            phone = jid[:match.start()]
            # Normalize: remove + if present, convert 964 to 0
            phone = phone.replace("+", "")
            if phone.startswith("964"):
                phone = "0" + phone[3:]
            # Validate Iraqi phone format
            if re.match(r'^0[67]\d{9}$', phone):
                return phone
        return None
    
    def export_to_csv(self, filename="whatsapp_numbers.csv"):
        """Export numbers to CSV"""
        print(f"\n💾 Exporting to {filename}...")
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["phone", "name"])
            for phone in sorted(self.numbers.keys()):
                writer.writerow([phone, self.numbers[phone]])
        
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
        print("📱 WhatsApp Number Extractor")
        print("=" * 50)
        
        # Check connection
        if not self.check_connection():
            return
        
        # Extract files
        if not self.extract_files():
            print("❌ Failed to extract WhatsApp files")
            return
        
        # Decrypt database
        db_path = self.decrypt_database()
        if not db_path:
            print("\n⚠️ Cannot decrypt database automatically.")
            print("\n📋 Manual extraction instructions:")
            print("1. Root your phone and install a file manager with root access")
            print("2. Navigate to /data/data/com.whatsapp/databases/")
            print("3. Copy msgstore.db.crypt14 and key files to /sdcard/")
            print("4. Pull them to your computer using: adb pull /sdcard/WhatsApp/ .")
            print("5. Use wa-crypt-tools to decrypt manually")
            print("\nOr try: pip install wa-crypt-tools")
            return
        
        # Extract numbers
        self.extract_numbers_from_db(db_path)
        
        if not self.numbers:
            print("\n⚠️ No phone numbers found")
            return
        
        # Export
        self.export_to_csv()
        
        # Cleanup
        self.cleanup()
        
        print("\n" + "=" * 50)
        print("✅ Done! Check whatsapp_numbers.csv")
        print("=" * 50)

if __name__ == "__main__":
    extractor = WhatsAppExtractor()
    extractor.run()
