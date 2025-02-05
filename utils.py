from passlib.context import CryptContext
from fastapi.responses import JSONResponse
from fastapi import Request, APIRouter, Depends, HTTPException
import jwt
import os
from datetime import datetime, timedelta
import logging
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from database import get_db
from sqlalchemy.orm import Session
from models import User
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from google.cloud import secretmanager

secret_client = secretmanager.SecretManagerServiceClient()

def access_secret_version(secret_id: str, version_id: str = "latest") -> str:

    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        secret_name = f"projects/{'skinsift-2024'}/secrets/{secret_id}/versions/{version_id}"
        response = secret_client.access_secret_version(name=secret_name)
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logging.error(f"Error accessing secret {secret_id}: {e}")
        raise

# Load secrets dari Secret Manager
try:
    SECRET_KEY = access_secret_version("secret_key")
    ACCESS_TOKEN_EXPIRE_DAYS = int(access_secret_version("ACCESS_TOKEN_EXPIRE_DAYS"))
    ALGORITHM = access_secret_version("ALGORITHM")
except Exception as e:
    raise ValueError("Error loading secrets: " + str(e))

def create_access_token(data: dict):
    """
    Membuat JWT access token dengan expiration.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})  # Tambahkan waktu expire ke payload
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# OAuth2PasswordBearer dependency
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

import uuid

def generate_unique_id() -> str:
    return uuid.uuid4().hex[:16]  # Mengambil 16 karakter pertama dari UUID


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        print(f"Decoded user_id: {user_id}")  # Debugging output
        if user_id is None:
            raise credentials_exception
        user = db.query(User).filter(User.Users_ID == user_id).first()
        if user is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return user
    
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )

async def validation_exception_handler(request: Request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

def create_response(
    status_code: int,
    message: str,
    data: Optional[Any] = None,
    data_key: Optional[str] = None  # Parameter tambahan
) -> Dict[str, Any]:
    is_error = not (200 <= status_code < 300)

    # Struktur dasar respons
    response = {
        "status_code": status_code,
        "error": is_error,
        "message": message,
    }

    if data is not None:
        # Gunakan kunci khusus jika disediakan, default ke "list" atau "data"
        key = data_key or ("list" if isinstance(data, list) else "data")
        response[key] = data

    return response
