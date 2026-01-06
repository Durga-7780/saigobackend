"""
Authentication Routes
Handles login, registration, and token management
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional

from app.config import settings
from app.models.employee import Employee, EmployeeCreate


router = APIRouter()

# Password hashing
# Note: Using pbkdf2_sha256 as primary for better compatibility across Python versions
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class Token(BaseModel):
    """Token response"""
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    """Token payload data"""
    employee_id: Optional[str] = None
    email: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request"""
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Registration request"""
    employee_data: EmployeeCreate


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


async def get_current_employee(token: str = Depends(oauth2_scheme)) -> Employee:
    """Get current authenticated employee"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        employee_id: str = payload.get("sub")
        
        if employee_id is None:
            raise credentials_exception
        
        token_data = TokenData(employee_id=employee_id)
    
    except JWTError:
        raise credentials_exception
    
    employee = await Employee.find_one(Employee.employee_id == token_data.employee_id)
    
    if employee is None:
        raise credentials_exception
    
    return employee


@router.post("/register", response_model=Token)
async def register(request: RegisterRequest):
    """
    Register a new employee
    """
    # Check if employee already exists
    existing = await Employee.find_one(Employee.email == request.employee_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    password_hash = get_password_hash(request.employee_data.password)
    
    # Create employee
    employee_dict = request.employee_data.dict(exclude={"password"})
    employee = Employee(**employee_dict, password_hash=password_hash)
    
    await employee.insert()
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": employee.employee_id, "email": employee.email},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login with email and password
    """
    # Find employee by email (username field contains email)
    employee = await Employee.find_one(Employee.email == form_data.username)
    
    if not employee or not verify_password(form_data.password, employee.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Update last login
    employee.last_login = datetime.utcnow()
    await employee.save()
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": employee.employee_id, "email": employee.email},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.get("/me")
async def get_current_user(current_employee: Employee = Depends(get_current_employee)):
    """
    Get current authenticated employee details
    """
    return {
        "employee_id": current_employee.employee_id,
        "name": f"{current_employee.first_name} {current_employee.last_name}",
        "email": current_employee.email,
        "department": current_employee.department,
        "designation": current_employee.designation,
        "role": current_employee.role,
        "profile_picture": current_employee.profile_picture
    }


@router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Change employee password
    """
    # Verify old password
    if not verify_password(old_password, current_employee.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password"
        )
    
    # Update password
    current_employee.password_hash = get_password_hash(new_password)
    await current_employee.save()
    
    return {"message": "Password changed successfully"}
