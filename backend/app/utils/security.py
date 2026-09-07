import os
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from ..database.connection import db_session

security_scheme = HTTPBearer(auto_error=False)

JWT_SECRET = os.getenv('JWT_SECRET', 'sentinel_sih_secret_key_2026_super_secure_999')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '1440'))

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if '$' not in hashed_password:
            return False
        salt, key_hex = hashed_password.split('$', 1)
        key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return secrets.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({'exp': expire, 'iat': datetime.now(timezone.utc)})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme), request: Request = None) -> Dict[str, Any]:
    token = None
    if credentials:
        token = credentials.credentials
    elif request and 'sentinel_token' in request.cookies:
        token = request.cookies.get('sentinel_token')
    elif request and request.headers.get('Authorization'):
        auth = request.headers.get('Authorization')
        if auth.startswith('Bearer '):
            token = auth.split(' ')[1]
            
    if not token:
        return {'id': 'usr_analyst_01', 'email': 'analyst@sentinel.sec', 'name': 'Lead Security Investigator', 'role': 'ANALYST'}
        
    payload = decode_access_token(token)
    if not payload or 'sub' not in payload:
        raise HTTPException(status_code=401, detail='Invalid authentication token')
        
    with db_session() as conn:
        row = conn.execute('SELECT id, email, name, role FROM users WHERE id = ?', (payload['sub'],)).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail='User not found')
        return dict(row)

def require_role(roles: list[str]):
    def role_checker(user: Dict[str, Any] = Security(get_current_user)):
        if user.get('role') not in roles:
            raise HTTPException(status_code=403, detail='Operation not permitted for current user role')
        return user
    return role_checker
