import os
import subprocess

# Auto-load Turso credentials from macOS Keychain BEFORE any other imports
# (data_layer establishes DB connection at import time)
# Store once with:
#   security add-generic-password -a tooltrick -s TURSO_AUTH_TOKEN -w "your-token"
#   security add-generic-password -a tooltrick -s TURSO_DATABASE_URL -w "your-url"
if not os.environ.get('TURSO_AUTH_TOKEN'):
    try:
        token = subprocess.check_output(
            ['security', 'find-generic-password', '-a', 'tooltrick', '-s', 'TURSO_AUTH_TOKEN', '-w'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        url = subprocess.check_output(
            ['security', 'find-generic-password', '-a', 'tooltrick', '-s', 'TURSO_DATABASE_URL', '-w'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        if token:
            os.environ['TURSO_AUTH_TOKEN'] = token
        if url:
            os.environ['TURSO_DATABASE_URL'] = url
    except Exception:
        pass  # Not on macOS or keychain entry not set — falls back to SQLite

from nicegui import ui
from data_layer import init_user_db, DB_STATUS

init_user_db()

print('=' * 60)
if DB_STATUS['backend'] == 'turso':
    print(f"✅ Connected to Turso database: {DB_STATUS['detail']}")
elif 'turso failed' in DB_STATUS['backend']:
    print(f"⚠️  Turso connection FAILED, using local SQLite instead.")
    print(f"    Reason: {DB_STATUS['detail']}")
    print(f"    Check: TURSO_DATABASE_URL / TURSO_AUTH_TOKEN env vars, and that 'libsql' is installed.")
else:
    print("ℹ️  Using local SQLite (no TURSO_DATABASE_URL / TURSO_AUTH_TOKEN found in environment).")
    print(f"    TURSO_DATABASE_URL set: {'TURSO_DATABASE_URL' in os.environ}")
    print(f"    TURSO_AUTH_TOKEN set: {'TURSO_AUTH_TOKEN' in os.environ}")
print('=' * 60)

# Importing each page module registers its @ui.page route
import page_import
import page_estimator
import page_autosolver
import page_training
import page_lineup
import page_predictor
import page_tstc
import page_boxplot
import page_config
import page_reference
import page_roster
import page_users

# Dynamic port binding for cloud deployment
port = int(os.environ.get('PORT', 8601))
storage_secret = os.environ.get('STORAGE_SECRET', 'hattrick-toolkit-dev-secret-change-me')

ui.run(
    host='0.0.0.0', 
    port=port, 
    storage_secret=storage_secret, 
    title='Tooltrick', 
    dark=True, 
    reload=False,
    reconnect_timeout=120.0  # Keep session alive during long solver runs
)