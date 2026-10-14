import hashlib, hmac, secrets, re
import database as db

_ITERATIONS = 310_000

def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${digest.hex()}"

def verify_password(password, encoded):
    try:
        scheme, rounds, salt_hex, digest_hex = encoded.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False

def valid_email(email):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()))

def register(username, email, password):
    username = username.strip()
    email = email.strip().lower()
    if len(username) < 3 or len(username) > 40:
        return False, "Username must be 3–40 characters."
    if not valid_email(email):
        return False, "Enter a valid email address."
    if len(password) < 10:
        return False, "Use a password with at least 10 characters."
    try:
        db.add_user(username, email, hash_password(password), "user")
        db.log_event(None, username, "ACCOUNT_REGISTERED", "SUCCESS", "New user account created")
        return True, "Account created. You can now sign in."
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            return False, "That username or email is already registered."
        return False, "Could not create the account. Check the application logs."

def login(login_value, password):
    user = db.get_user_by_login(login_value)
    if not user or not verify_password(password, user["password_hash"]):
        db.log_event(None, login_value[:80] or "unknown", "LOGIN", "ERROR", "Invalid credentials")
        return None, "Incorrect username/email or password."
    if not user["active"]:
        db.log_event(user["id"], user["username"], "LOGIN", "ERROR", "Inactive account")
        return None, "This account is disabled. Contact the administrator."
    db.log_event(user["id"], user["username"], "LOGIN", "SUCCESS", "Signed in")
    return dict(user), ""
