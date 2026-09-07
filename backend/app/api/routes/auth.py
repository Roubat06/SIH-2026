from fastapi import APIRouter, HTTPException, Depends, Response
from ...database.connection import db_session
from ...utils.security import hash_password, verify_password, create_access_token, get_current_user
from ...schemas.models import UserCreate, UserLogin, TokenResponse, UserResponse
from ...services.audit import log_audit_event
import secrets
from datetime import datetime, timezone

router = APIRouter(prefix='/api/auth', tags=['Authentication'])

@router.post('/register', response_model=TokenResponse)
def register_user(user_in: UserCreate, response: Response):
    now_iso = datetime.now(timezone.utc).isoformat()
    with db_session() as conn:
        existing = conn.execute('SELECT id FROM users WHERE email = ?', (user_in.email.lower(),)).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail='Email address already registered')
            
        user_id = f'usr_{secrets.token_hex(6)}'
        pw_hash = hash_password(user_in.password)
        conn.execute('''
            INSERT INTO users (id, email, name, role, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, user_in.email.lower(), user_in.name, user_in.role.upper(), pw_hash, now_iso, now_iso))
        
        token = create_access_token({'sub': user_id, 'email': user_in.email.lower(), 'role': user_in.role.upper()})
        response.set_cookie('sentinel_token', token, httponly=True, samesite='lax')
        
        log_audit_event(action='user_registered', target_type='user', target_id=user_id, actor_id=user_id, actor_name=user_in.name, conn=conn)
        
        user_resp = UserResponse(id=user_id, email=user_in.email.lower(), name=user_in.name, role=user_in.role.upper(), created_at=now_iso)
        return TokenResponse(access_token=token, token_type='bearer', user=user_resp)

@router.post('/login', response_model=TokenResponse)
def login_user(creds: UserLogin, response: Response):
    with db_session() as conn:
        user = conn.execute('SELECT * FROM users WHERE email = ?', (creds.email.lower(),)).fetchone()
        if not user or not verify_password(creds.password, user['password_hash']):
            raise HTTPException(status_code=401, detail='Invalid email or password credentials')
            
        token = create_access_token({'sub': user['id'], 'email': user['email'], 'role': user['role']})
        response.set_cookie('sentinel_token', token, httponly=True, samesite='lax')
        
        log_audit_event(action='user_login', target_type='user', target_id=user['id'], actor_id=user['id'], actor_name=user['name'], conn=conn)

        
        user_resp = UserResponse(id=user['id'], email=user['email'], name=user['name'], role=user['role'], created_at=user['created_at'])
        return TokenResponse(access_token=token, token_type='bearer', user=user_resp)

@router.get('/me', response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user['id'],
        email=current_user['email'],
        name=current_user['name'],
        role=current_user['role'],
        created_at=current_user.get('created_at')
    )

@router.post('/logout')
def logout(response: Response):
    response.delete_cookie('sentinel_token')
    return {'message': 'Successfully signed out'}
