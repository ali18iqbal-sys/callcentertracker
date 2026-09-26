"""
convert_to_toml.py — users.yaml ko Streamlit Secrets TOML format mein convert karo
"""

import yaml
from pathlib import Path

# users.yaml load karo
with open("users.yaml", "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

# TOML banao
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
print("✅ streamlit_secrets.toml ban gaya!")
print("=" * 60)
print()
print("Ab is file ka content copy karein aur Streamlit Secrets mein paste karein.")
print()
print("File location: " + str(Path("streamlit_secrets.toml").absolute()))