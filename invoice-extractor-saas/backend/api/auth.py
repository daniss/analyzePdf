from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional
import jwt as pyjwt

from core.config import settings
from schemas.auth import UserCreate, UserResponse, Token, SubscriptionInfo
from models.user import User
from models.subscription import Subscription
from core.database import get_db
from core.security import verify_password, get_password_hash
from crud.user import (
    create_user, get_user_by_email, get_user_by_id, authenticate_user
)
from core.quota_manager import QuotaManager
from sqlalchemy.orm import selectinload

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


async def user_to_response(user: User, db: AsyncSession) -> UserResponse:
    """Convert User model to UserResponse with subscription info"""
    subscription_info = None
    if user.subscription:
        # Get accurate usage count from quota manager
        quota_status = await QuotaManager.get_quota_status(db, user.id)
        
        subscription_info = SubscriptionInfo(
            pricing_tier=user.subscription.pricing_tier,
            status=user.subscription.status,
            monthly_invoice_limit=user.subscription.monthly_invoice_limit,
            monthly_invoices_processed=quota_status.get('current_usage', 0),
            current_period_end=user.subscription.current_period_end
        )
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
        company_name=user.company_name,
        subscription=subscription_info
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = pyjwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = pyjwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except pyjwt.PyJWTError:
        raise credentials_exception
    
    # Get user from database
    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    existing_user = await get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        # Create new user
        db_user = await create_user(db, user)
        
        return await user_to_response(db_user, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )


@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # Authenticate user
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
async def refresh_access_token(current_user: User = Depends(get_current_user)):
    """Refresh access token for authenticated user"""
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(current_user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await user_to_response(current_user, db)


@router.get("/quota-status")
async def get_quota_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current quota status for authenticated user"""
    quota_status = await QuotaManager.get_quota_status(db, current_user.id)
    return quota_status