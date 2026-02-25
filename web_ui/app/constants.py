"""
Constants for the STT Web UI application.
"""

# Admin password hash (bcrypt with 12 rounds)
# Original password: gksxn2026!
ADMIN_PASSWORD_HASH = "$2b$12$6kIvIOUecXSKUPdX/ApfOOdDbjCV/h0LorXq6dSP0JGIvP/Kkucs2"

# Storage quota default (40GB in bytes)
DEFAULT_STORAGE_QUOTA = 42949672960  # 40 * 1024 * 1024 * 1024

# Admin session timeout (30 minutes in seconds)
ADMIN_SESSION_TIMEOUT = 1800

# Employee ID validation
EMPLOYEE_ID_LENGTH = 6
