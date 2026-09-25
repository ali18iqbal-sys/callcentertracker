"""
translate_to_english.py — Roman Urdu ko English mein badlo
Ek baar chalayein, sab files update ho jayengi.
"""

from pathlib import Path

# ─────────────── Translations ───────────────
TRANSLATIONS = {
    # Common phrases
    "Dono files upload karein — phir Merge button enable hoga.": "Upload both files to enable the Merge button.",
    "Dono taraf kam az kam ek file upload karein.": "Upload at least one file on both sides.",
    "Dono taraf kam az kam ek file upload karein — phir Merge enable hoga.": "Upload at least one file on both sides to enable Merge.",
    "Pehle upload aur merge karein": "Please upload and merge first",
    "Pehle se loaded": "Already loaded",
    "Pehle se loaded:": "Already loaded:",
    "Left sidebar se": "From the left sidebar, open",
    "kholein": "open",
    "Page load ho gaya!": "Page loaded successfully!",
    "Auto-Fetch ready": "Auto-Fetch Ready",
    "Deployment aage aayega": "Deployment coming next",
    "Phase complete": "Phase Complete",
    
    # Upload page
    "Client ki sales file aur Call Center ki calls file upload karein": "Upload the client sales file and call center calls file",
    "Ek ya zyada files upload karein — sab auto-combine ho jayengi": "Upload one or more files — they will be auto-combined",
    "Ek ya zyada files — Google Sheet / XLSX / CSV / JSON": "One or more files — Google Sheet / XLSX / CSV / JSON",
    "Ek ya zyada files (team-wise bhi ho sakti hain)": "One or more files (can be team-wise)",
    "Client files choose karein": "Choose client files",
    "Call Center files choose karein": "Choose call center files",
    "client file choose karein": "choose client file",
    "Call Center file choose karein": "choose call center file",
    "file(s) loaded": "file(s) loaded",
    "Preview (pehli 5 rows)": "Preview (first 5 rows)",
    "Columns detected": "Columns detected",
    "Koi standard column nahi mila": "No standard columns detected",
    "Files": "Files",
    "file(s) skip hui": "file(s) skipped",
    "Standard columns": "Standard Columns",
    "Extra columns": "Extra Columns",
    "File type support nahi hai": "File type not supported",
    "MERGE & ANALYZE": "MERGE & ANALYZE",
    "Merge complete! Left sidebar se": "Merge complete! From the left sidebar, open",
    "Result screen par jayein": "Go to the Results page",
    "rows filter out (price khali/0/negative)": "rows filtered out (price empty/0/negative)",
    "Client data mein phone column nahi mila": "Phone column not found in client data",
    "CC data mein phone column nahi mila": "Phone column not found in CC data",
    "Merge error": "Merge Error",
    "Error details": "Error Details",
    "Clear All Data": "Clear All Data",
    
    # Results page
    "Merge Results": "Merge Results",
    "Summary": "Summary",
    "Sold (matched)": "Sold (Matched)",
    "No-Sale (CC only)": "No-Sale (CC Only)",
    "Orphan (Client only)": "Orphan (Client Only)",
    "Woh calls jinke against sale hui": "Calls that resulted in a sale",
    "CC mein calls hui lekin client mein sale nahi": "Calls logged in CC but no sale on client side",
    "Client mein sale hai lekin CC mein call nahi mili": "Sales on client side but no matching call in CC",
    "Koi sold record nahi": "No sold records",
    "Koi no-sale record nahi": "No no-sale records",
    "Koi orphan record nahi": "No orphan records",
    "Download Sold (Excel)": "Download Sold (Excel)",
    "Download No-Sale (Excel)": "Download No-Sale (Excel)",
    "Download Orphan (Excel)": "Download Orphan (Excel)",
    
    # Performance page
    "Performance Dashboard": "Performance Dashboard",
    "Overall Performance": "Overall Performance",
    "Team-wise": "Team-wise",
    "Dialer-wise": "Dialer-wise",
    "Team-wise performance (amount ke hisaab se sorted)": "Team-wise performance (sorted by amount)",
    "Dialer-wise performance (amount ke hisaab se sorted)": "Dialer-wise performance (sorted by amount)",
    "Team data nahi mila — CC file mein 'Team' column hona chahiye": "Team data not found — CC file must have a 'Team' column",
    "Dialer data nahi mila — CC file mein 'Dialer' column hona chahiye": "Dialer data not found — CC file must have a 'Dialer' column",
    "Download Team Performance (Excel)": "Download Team Performance (Excel)",
    "Download Dialer Performance (Excel)": "Download Dialer Performance (Excel)",
    "Conversion %": "Conversion %",
    
    # Missing page
    "Missing / Mismatch Report": "Missing / Mismatch Report",
    "Yeh report dikhati hai ke kahan data match nahi hua": "This report shows where data did not match",
    "Orphan Sales": "Orphan Sales",
    "No-Sale Calls": "No-Sale Calls",
    "Client sheet mein hai, lekin Call Center ki file mein call nahi mili": "Present in client sheet but no matching call in Call Center file",
    "phone # client mein hain lekin CC ki file mein nahi mile": "phone numbers in client but not found in CC file",
    "calls jinke against sale nahi hui": "calls with no sale",
    "Koi orphan record nahi — sab client phones CC mein mile": "No orphan records — all client phones found in CC",
    "Koi no-sale call nahi — sab calls par sale hui!": "No no-sale calls — all calls resulted in sales!",
    "Download Orphan (Excel)": "Download Orphan (Excel)",
    "Download No-Sale (Excel)": "Download No-Sale (Excel)",
    "Possible reasons:": "Possible Reasons:",
    "Yeh calls valid hain": "These calls are valid",
    "Team/Dialer performance mein yeh 'effort without sale' hain": "In Team/Dialer performance, these are 'efforts without sale'",
    "CC ki file adhoori hai (kuch dialers ka data missing)": "CC file is incomplete (some dialers' data missing)",
    "Phone # ka format alag hai (auto-fix ho chuka hai)": "Phone # format differs (auto-fix applied)",
    "Client ne ghalat phone # bheja": "Client sent wrong phone #",
    
    # Reports page
    "Custom Report Builder": "Custom Report Builder",
    "Apni calculation banayein, filter lagayein, report download karein": "Build your own calculation, apply filters, download report",
    "Data loaded": "Data loaded",
    "Filters": "Filters",
    "Date column": "Date Column",
    "Date range": "Date Range",
    "Date filter lagayein": "Apply date filter",
    "Koi date column nahi mila": "No date column found",
    "Status (Sold / No-Sale / Orphan)": "Status (Sold / No-Sale / Orphan)",
    "Filtered": "Filtered",
    "Custom Calculation": "Custom Calculation",
    "Naya calculated column add karein": "Add new calculated column",
    "Column A": "Column A",
    "Operation": "Operation",
    "Column B": "Column B",
    "Output column name": "Output Column Name",
    "Column B zaroori nahi": "Column B not required",
    "Apply Calculation": "Apply Calculation",
    "Calculated column active hai": "Calculated column is active",
    "Calculated columns reset karein": "Reset Calculated Columns",
    "Group Report": "Group Report",
    "Koi grouping nahi": "(No Grouping)",
    "Group by": "Group By",
    "Metric column": "Metric Column",
    "Sirf count": "(Count Only)",
    "Aggregation": "Aggregation",
    "Report Generate Karein": "Generate Report",
    "Report Result": "Report Result",
    "Download Report (Excel)": "Download Report (Excel)",
    "Koi data nahi mila": "No data found",
    "Report error": "Report Error",
    "Calls & Records Summary": "Calls & Records Summary",
    "Numeric Columns Summary": "Numeric Columns Summary",
    "Sirf metric columns (phone/ID skip ho gaye)": "Only metric columns (phone/ID excluded)",
    "Columns select karein": "Select columns",
    "Download Summary (Excel)": "Download Summary (Excel)",
    "Koi valid numeric column nahi mila": "No valid numeric columns found",
    "Filtered Data Preview (full)": "Filtered Data Preview (full)",
    "Download Full Filtered Data (Excel)": "Download Full Filtered Data (Excel)",
    
    # Target page
    "Target Setup": "Target Setup",
    "Daily call targets set karein — monthly target auto calculate hoga": "Set daily call targets — monthly target will auto-calculate",
    "Daily Call Targets": "Daily Call Targets",
    "Har din ka call target define karein": "Define call target for each day type",
    "Weekday (Mon-Fri)": "Weekday (Mon-Fri)",
    "Saturday": "Saturday",
    "Sunday": "Sunday",
    "Holiday": "Holiday",
    "Monthly Target (Auto-Calculated)": "Monthly Target (Auto-Calculated)",
    "Team-wise Targets (Optional)": "Team-wise Targets (Optional)",
    "Khali chhorein agar team-wise target nahi chahiye": "Leave empty if team-wise targets not required",
    "Kitni teams hain?": "How many teams?",
    "Team naam": "Team Name",
    "Team target": "Team Target",
    "Dialer-wise Targets (Optional)": "Dialer-wise Targets (Optional)",
    "Kitne dialers hain?": "How many dialers?",
    "Dialer naam": "Dialer Name",
    "Dialer target": "Dialer Target",
    "Save All Targets": "Save All Targets",
    "Targets save ho gaye!": "Targets saved successfully!",
    "Day Type": "Day Type",
    "Days": "Days",
    "Per Day": "Per Day",
    "Total": "Total",
    "Total Days": "Total Days",
    "Monthly Target": "Monthly Target",
    "Weighted Avg/Day": "Weighted Avg/Day",
    "Weekdays (Mon-Fri)": "Weekdays (Mon-Fri)",
    "Saturdays": "Saturdays",
    "Sundays": "Sundays",
    "Holidays": "Holidays",
    
    # Admin page
    "Master Panel": "Master Panel",
    "Users manage karein — add, edit, disable, password change": "Manage users — add, edit, disable, change password",
    "Users": "Users",
    "Add User": "Add User",
    "Change Password": "Change Password",
    "User List": "User List",
    "User Actions": "User Actions",
    "User choose karein": "Choose user",
    "Role badlo": "Change Role",
    "admin delete nahi ho sakta": "(admin cannot be deleted)",
    "Enable Karo": "Enable",
    "Disable Karo": "Disable",
    "Save Role": "Save Role",
    "Delete Karo": "Delete",
    "Koi user nahi mila": "No users found",
    "Naya User Add Karein": "Add New User",
    "Username": "Username",
    "Full Name": "Full Name",
    "Email": "Email",
    "Role": "Role",
    "Password": "Password",
    "Confirm Password": "Confirm Password",
    "Add User": "Add User",
    "Username aur Password zaroori hain": "Username and Password are required",
    "Password kam az kam 6 characters ka hona chahiye": "Password must be at least 6 characters",
    "Dono passwords match nahi kar rahe": "Passwords do not match",
    "Username mein space nahi ho sakta": "Username cannot contain spaces",
    "Password Change Karein": "Change Password",
    "Naya Password": "New Password",
    "Confirm Naya Password": "Confirm New Password",
    "Password zaroori hai": "Password is required",
    "Sirf Master role wale hi is page ko access kar sakte hain": "Only Master role users can access this page",
    "add ho gaya": "added successfully",
    "update ho gaya": "updated successfully",
    "delete ho gaya": "deleted successfully",
    "disabled ho gaya": "disabled",
    "enabled ho gaya": "enabled",
    
    # Data Sources page
    "Auto Data Sources": "Auto Data Sources",
    "Google Sheet ya API se direct data fetch karein": "Fetch data directly from Google Sheet or API",
    "Google Sheets": "Google Sheets",
    "APIs": "APIs",
    "Currently Loaded Data": "Currently Loaded Data",
    "Client Data": "Client Data",
    "Call Center Data": "Call Center Data",
    "Fetch ke baad Upload page par jayein aur Merge button dabayein": "After fetching, go to Upload page and click Merge",
    "Google Sheet Sources": "Google Sheet Sources",
    "Koi Google Sheet source add nahi kiya": "No Google Sheet source added",
    "Client Sales": "Client Sales",
    "Call Center (Calls)": "Call Center (Calls)",
    "Add Naya Google Sheet": "Add New Google Sheet",
    "Sheet URL": "Sheet URL",
    "Data Type": "Data Type",
    "Sheet Tab (optional)": "Sheet Tab (optional)",
    "Credentials Path": "Credentials Path",
    "Add Source": "Add Source",
    "Name aur URL zaroori hain": "Name and URL are required",
    "Fetch Now": "Fetch Now",
    "Delete": "Delete",
    "rows fetch hue": "rows fetched",
    "API Sources": "API Sources",
    "Koi API source add nahi kiya": "No API source added",
    "Add Naya API Source": "Add New API Source",
    "Endpoint URL": "Endpoint URL",
    "Auth Type": "Auth Type",
    "No Auth": "No Auth",
    "Bearer Token": "Bearer Token",
    "API Key": "API Key",
    "Token/Key": "Token/Key",
    "JSON Path (optional)": "JSON Path (optional)",
    "Credentials file nahi mili": "Credentials file not found",
    "Service Account Setup Guide": "Service Account Setup Guide",
    "Test API Example": "Test API Example",
    "Name": "Name",
    "URL": "URL",
    "Tab": "Tab",
    "Auth": "Auth",
    "JSON Path": "JSON Path",
    "Preview": "Preview",
    
    # Login page
    "Sales Conversion Tracking System": "Sales Conversion Tracking System",
    "Demo credentials": "Demo credentials",
    "Username ya password ghalat hai": "Invalid username or password",
    "Login": "Login",
    
    # app.py
    "User": "User",
    "Logout": "Logout",
    "Upload": "Upload",
    "Data Sources": "Data Sources",
    "Results": "Results",
    "Performance": "Performance",
    "Missing": "Missing",
    "Targets": "Targets",
    "Reports": "Reports",
    "Master Panel": "Master Panel",
    "Auto-Fetch ready": "Auto-Fetch Ready",
    "Phase complete": "Phase Complete",
    "Deployment aage aayega": "Deployment coming next",
    "User: ": "User: ",
    "Master": "Master",
    "User": "User",
    "Navigation": "Navigation",
}

# ─────────────── Files to update ───────────────
FILES_TO_UPDATE = [
    "app.py",
    "app/pages/upload_page.py",
    "app/pages/results_page.py",
    "app/pages/performance_page.py",
    "app/pages/missing_page.py",
    "app/pages/report_page.py",
    "app/pages/target_page.py",
    "app/pages/admin_page.py",
    "app/pages/data_sources_page.py",
    "app/pages/login_page.py",
]

# ─────────────── Run ───────────────
print("=" * 60)
print("TRANSLATION: Roman Urdu → English")
print("=" * 60)

total_changes = 0

for filepath in FILES_TO_UPDATE:
    path = Path(filepath)
    if not path.exists():
        print(f"SKIP: {filepath} (not found)")
        continue
    
    content = path.read_text(encoding="utf-8")
    original = content
    changes = 0
    
    # Sort by length (longest first) to avoid partial replacements
    for urdu, english in sorted(TRANSLATIONS.items(), key=lambda x: -len(x[0])):
        if urdu in content:
            count = content.count(urdu)
            content = content.replace(urdu, english)
            changes += count
    
    if content != original:
        path.write_text(content, encoding="utf-8")
        print(f"OK: {filepath} ({changes} replacements)")
        total_changes += changes
    else:
        print(f"--: {filepath} (no changes)")

print("")
print("=" * 60)
print(f"DONE - Total {total_changes} replacements")
print("=" * 60)
print("")
print("Next steps:")
print("  1. Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force")
print("  2. streamlit run app.py    (local test)")
print("  3. git add . && git commit -m 'Translate UI to English' && git push")