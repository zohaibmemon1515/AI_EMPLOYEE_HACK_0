import csv
import json
from pathlib import Path
from datetime import datetime


def clean_phone(phone):

    phone = ''.join(c for c in phone if c.isdigit() or c == '+')

    if phone.startswith('0'):
        phone = '+92' + phone[1:]

    elif phone.startswith('3') and len(phone) == 10:
        phone = '+92' + phone

    elif not phone.startswith('+'):
        phone = '+' + phone

    return phone


def convert_google_csv(csv_file, output_file):

    contacts = {}

    with open(csv_file, 'r', encoding='utf-8') as f:

        reader = csv.DictReader(f)

        print("CSV Columns:", reader.fieldnames)

        for row in reader:

            name = (
                row.get('Name') or
                row.get('Given Name') or
                row.get('First Name') or
                ''
            ).strip()

            phone = (
                row.get('Phone 1 - Value') or
                row.get('Phone') or
                row.get('Mobile') or
                ''
            ).strip()

            if not name or not phone:
                continue

            phone = clean_phone(phone)

            key = name.lower()

            contacts[key] = {
                "name": name,
                "phone": phone,
                "added": datetime.now().isoformat(),
                "last_used": datetime.now().isoformat()
            }

    Path("Vault/Contacts").mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(contacts, f, indent=2)

    print(f"✅ Converted {len(contacts)} contacts")
    print(f"📁 Saved to: {output_file}")


if __name__ == "__main__":

    import sys

    csv_file = sys.argv[1] if len(sys.argv) > 1 else "contacts.csv"

    convert_google_csv(csv_file, "Vault/Contacts/contacts.json")