"""Small FastAPI inventory API. Run from backend with uvicorn main:app."""
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Annotated

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator
from pwdlib import PasswordHash
from sqlalchemy import CheckConstraint, Integer, Numeric, String, create_engine, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

load_dotenv(Path(__file__).with_name('.env'))
MAX_STOCK = 2_147_483_647

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default='user')

class Vehicle(Base):
    __tablename__ = 'vehicles'
    __table_args__ = (CheckConstraint(f'quantity >= 0 AND quantity <= {MAX_STOCK}'), CheckConstraint('price >= 0'))
    id: Mapped[int] = mapped_column(primary_key=True)
    make: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(100))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int] = mapped_column(Integer)

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Login(Input):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator('email')
    @classmethod
    def email_format(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Enter a valid email address')
        return value

class Registration(Login):
    password: str = Field(min_length=8, max_length=128)

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    role: str

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Price = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)]

class VehicleCreate(Input):
    make: Name
    model: Name
    category: Name
    price: Price
    quantity: int = Field(ge=0, le=MAX_STOCK, strict=True)

class VehicleUpdate(Input):
    # Stock changes must use purchase/restock, so PUT cannot bypass admin checks.
    make: Name | None = None
    model: Name | None = None
    category: Name | None = None
    price: Price | None = None

    @model_validator(mode='after')
    def nonempty(self):
        if not self.model_fields_set or any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError('Provide at least one non-null vehicle detail')
        return self

class VehicleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    make: str
    model: str
    category: str
    price: Decimal
    quantity: int

class StockChange(Input):
    quantity: int = Field(gt=0, le=MAX_STOCK, strict=True)


def create_app():
    secret = os.getenv('JWT_SECRET_KEY', '')
    if len(secret) < 32 or secret.startswith('replace-'):
        raise RuntimeError('Set JWT_SECRET_KEY to a random secret of at least 32 characters')
    algorithm = os.getenv('JWT_ALGORITHM', 'HS256')
    if algorithm != 'HS256':
        raise RuntimeError('This MVP supports JWT_ALGORITHM=HS256 only')
    minutes = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
    if minutes <= 0:
        raise RuntimeError('ACCESS_TOKEN_EXPIRE_MINUTES must be positive')
    engine = create_engine(os.getenv('DATABASE_URL', 'sqlite:///./dealership.db'), connect_args={'check_same_thread': False, 'timeout': 30})
    hasher = PasswordHash.recommended()
    dummy_hash = hasher.hash('non-account timing placeholder')

    @asynccontextmanager
    async def lifespan(app):
        Base.metadata.create_all(engine)
        yield
        engine.dispose()

    app = FastAPI(title='Car Dealership Inventory', lifespan=lifespan)
    app.state.engine = engine
    app.add_middleware(CORSMiddleware, allow_origins=[os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173')], allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Authorization', 'Content-Type'])
    bearer = HTTPBearer(auto_error=False)

    def database():
        with Session(engine) as session:
            yield session

    def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(database)):
        unauthorized = HTTPException(401, 'Invalid or missing authentication', headers={'WWW-Authenticate': 'Bearer'})
        if credentials is None:
            raise unauthorized
        try:
            claims = jwt.decode(credentials.credentials, secret, algorithms=[algorithm], options={'require': ['sub', 'exp']})
            user_id = int(claims['sub'])
        except (jwt.InvalidTokenError, ValueError, TypeError):
            raise unauthorized
        user = db.get(User, user_id)
        if user is None:
            raise unauthorized
        return user

    def admin(user: User = Depends(current_user)):
        if user.role != 'admin':
            raise HTTPException(403, 'Admin access required')
        return user

    def get_vehicle(db, vehicle_id):
        item = db.get(Vehicle, vehicle_id)
        if item is None:
            raise HTTPException(404, 'Vehicle not found')
        return item

    @app.post('/api/auth/register', response_model=UserOut, status_code=201)
    def register(data: Registration, db: Session = Depends(database)):
        user = User(email=data.email, password_hash=hasher.hash(data.password), role='user')
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'Email already registered')
        db.refresh(user)
        return user

    @app.post('/api/auth/login')
    def login(data: Login, db: Session = Depends(database)):
        user = db.scalar(select(User).where(User.email == data.email))
        valid = hasher.verify(data.password, user.password_hash if user else dummy_hash)
        if not user or not valid:
            raise HTTPException(401, 'Invalid email or password', headers={'WWW-Authenticate': 'Bearer'})
        token = jwt.encode({'sub': str(user.id), 'exp': datetime.now(timezone.utc) + timedelta(minutes=minutes)}, secret, algorithm=algorithm)
        return {'access_token': token, 'token_type': 'bearer', 'user': UserOut.model_validate(user)}

    @app.post('/api/vehicles', response_model=VehicleOut, status_code=201)
    def create_vehicle(data: VehicleCreate, user: User = Depends(current_user), db: Session = Depends(database)):
        item = Vehicle(**data.model_dump())
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @app.get('/api/vehicles', response_model=list[VehicleOut])
    def list_vehicles(user: User = Depends(current_user), db: Session = Depends(database)):
        return db.scalars(select(Vehicle).order_by(Vehicle.id)).all()

    @app.get('/api/vehicles/search', response_model=list[VehicleOut])
    def search(q: str | None = None, make: str | None = None, model: str | None = None, category: str | None = None,
               min_price: Decimal | None = Query(None, ge=0, allow_inf_nan=False), max_price: Decimal | None = Query(None, ge=0, allow_inf_nan=False),
               user: User = Depends(current_user), db: Session = Depends(database)):
        if min_price is not None and max_price is not None and min_price > max_price:
            raise HTTPException(422, 'min_price must not exceed max_price')
        statement = select(Vehicle)
        for field, value in [(Vehicle.make, make), (Vehicle.model, model), (Vehicle.category, category)]:
            if value:
                statement = statement.where(field.icontains(value, autoescape=True))
        if q:
            statement = statement.where(or_(*(field.icontains(q, autoescape=True) for field in [Vehicle.make, Vehicle.model, Vehicle.category])))
        if min_price is not None:
            statement = statement.where(Vehicle.price >= min_price)
        if max_price is not None:
            statement = statement.where(Vehicle.price <= max_price)
        return db.scalars(statement.order_by(Vehicle.id)).all()

    @app.put('/api/vehicles/{vehicle_id}', response_model=VehicleOut)
    def edit(vehicle_id: int, data: VehicleUpdate, user: User = Depends(current_user), db: Session = Depends(database)):
        item = get_vehicle(db, vehicle_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        db.commit()
        db.refresh(item)
        return item

    @app.delete('/api/vehicles/{vehicle_id}', status_code=204)
    def delete(vehicle_id: int, user: User = Depends(admin), db: Session = Depends(database)):
        db.delete(get_vehicle(db, vehicle_id))
        db.commit()
        return Response(status_code=204)

    def change_stock(db, vehicle_id, quantity, restock=False):
        # Conditional UPDATE is atomic, even if simultaneous buyers see the same stock.
        condition = Vehicle.quantity <= MAX_STOCK - quantity if restock else Vehicle.quantity >= quantity
        amount = quantity if restock else -quantity
        result = db.execute(update(Vehicle).where(Vehicle.id == vehicle_id, condition).values(quantity=Vehicle.quantity + amount))
        if result.rowcount != 1:
            db.rollback()
            get_vehicle(db, vehicle_id)
            raise HTTPException(409, 'Stock limit exceeded' if restock else 'Insufficient stock')
        db.commit()
        return get_vehicle(db, vehicle_id)

    @app.post('/api/vehicles/{vehicle_id}/purchase', response_model=VehicleOut)
    def purchase(vehicle_id: int, data: StockChange, user: User = Depends(current_user), db: Session = Depends(database)):
        return change_stock(db, vehicle_id, data.quantity)

    @app.post('/api/vehicles/{vehicle_id}/restock', response_model=VehicleOut)
    def restock(vehicle_id: int, data: StockChange, user: User = Depends(admin), db: Session = Depends(database)):
        return change_stock(db, vehicle_id, data.quantity, restock=True)

    return app

app = create_app()
