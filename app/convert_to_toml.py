"""
convert_to_toml.py — Convert users.yaml into the Streamlit Secrets TOML format.

Usage (from the project root):

    python app/convert_to_toml.py

The generated file is written to streamlit_secrets.toml, which is git-ignored.
Review it and paste the contents into your Streamlit Secrets settings.
"""

import yaml
from pathlib import Path

# Load users.yaml
with open("users.yaml", "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

# Build the TOML document
lines = ["[users]", ""]

# Credentials
users = data.get("credentials", {}).get("usernames", {})
for username, info in users.items():
    lines.append(f"[users.credentials.usernames.{username}]")
    lines.append(f'email = "{info.get("email", "")}"')
    lines.append(f'name = "{info.get("name", "")}"')
    lines.append(f'password = "{info.get("password", "")}"')
    lines.append(f'role = "{info.get("role", "user")}"')
    lines.append("")

# Cookie
cookie = data.get("cookie", {})
lines.append("[users.cookie]")
lines.append(f'expiry_days = {cookie.get("expiry_days", 1)}')
lines.append(f'key = "{cookie.get("key", "")}"')
lines.append(f'name = "{cookie.get("name", "")}"')
lines.append("")

# Preauthorized
lines.append("[users.preauthorized]")
lines.append("emails = []")

# Save
output = "\n".join(lines)
Path("streamlit_secrets.toml").write_text(output, encoding="utf-8")

print("=" * 60)
print("streamlit_secrets.toml has been generated.")
print("=" * 60)
print()
print("Copy the contents of this file into your Streamlit Secrets settings.")
print()
print("File location: " + str(Path("streamlit_secrets.toml").absolute()))