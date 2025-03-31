from sqlalchemy.orm import Session
from . import models, schemas
import secrets
import string
from datetime import datetime
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def generate_short_code(length: int = 6) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

def get_link_by_short_code(db: Session, short_code: str):
    return db.query(models.Link).filter(models.Link.short_code == short_code).first()

def create_link(db: Session, link: schemas.LinkCreate):
    short_code = generate_short_code()
    while get_link_by_short_code(db, short_code):
        short_code = generate_short_code()
    
    db_link = models.Link(
        original_url=link.original_url,
        short_code=short_code
    )
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link

def update_link(db: Session, short_code: str, link_update: schemas.LinkUpdate):
    db_link = get_link_by_short_code(db, short_code)
    if not db_link:
        return None
    
    if link_update.original_url is not None:
        db_link.original_url = link_update.original_url
    if link_update.is_active is not None:
        db_link.is_active = link_update.is_active
    
    db.commit()
    db.refresh(db_link)
    return db_link

def delete_link(db: Session, short_code: str):
    db_link = get_link_by_short_code(db, short_code)
    if not db_link:
        return False
    
    db.delete(db_link)
    db.commit()
    return True

def increment_clicks(db: Session, short_code: str):
    db_link = get_link_by_short_code(db, short_code)
    if db_link:
        db_link.clicks += 1
        db.commit()
        db.refresh(db_link)
    return db_link

def get_link_stats(db: Session, short_code: str):
    return db.query(
        models.Link.original_url,
        models.Link.short_code,
        models.Link.created_at,
        models.Link.last_accessed_at,
        models.Link.clicks,
        models.Link.expires_at
    ).filter(models.Link.short_code == short_code).first()

def create_custom_link(db: Session, link: schemas.LinkCreate):
    if link.custom_alias:
        if get_link_by_short_code(db, link.custom_alias):
            raise ValueError("Custom alias already exists")
        short_code = link.custom_alias
    else:
        short_code = generate_short_code()
        while get_link_by_short_code(db, short_code):
            short_code = generate_short_code()
    
    db_link = models.Link(
        original_url=link.original_url,
        short_code=short_code,
        custom_alias=link.custom_alias,
        expires_at=link.expires_at
    )
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link

def search_by_original_url(db: Session, original_url: str):
    return db.query(models.Link).filter(
        models.Link.original_url.like(f"%{original_url}%")
    ).all()

def get_expired_links(db: Session):
    return db.query(models.Link).filter(
        models.Link.expires_at <= datetime.now()
    ).all()

def get_link_stats(db: Session, short_code: str):
    link = db.query(models.Link).filter(models.Link.short_code == short_code).first()
    if not link:
        return None
    return {
        "original_url": link.original_url,
        "short_code": link.short_code,
        "created_at": link.created_at,
        "last_accessed_at": link.last_accessed_at,
        "clicks": link.clicks,
        "expires_at": link.expires_at,
        "is_active": link.is_active
    }

def create_link_with_alias(db: Session, link: schemas.LinkCreate, user_id: int = None):
    # Проверяем кастомный алиас
    if link.custom_alias:
        if db.query(models.Link).filter(
            (models.Link.short_code == link.custom_alias) |
            (models.Link.custom_alias == link.custom_alias)
        ).first():
            raise ValueError("Custom alias already exists")
        short_code = link.custom_alias
    else:
        short_code = generate_short_code()
    
    # Создаем ссылку (с user_id или без)
    db_link = models.Link(
        original_url=link.original_url,
        short_code=short_code,
        custom_alias=link.custom_alias,
        expires_at=link.expires_at,
        user_id=user_id  # Может быть None
    )
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link

def search_links(db: Session, original_url: str):
    return db.query(models.Link).filter(
        models.Link.original_url.contains(original_url)
    ).all()

def delete_expired_links(db: Session):
    expired = db.query(models.Link).filter(
        models.Link.expires_at <= datetime.now()
    ).all()
    for link in expired:
        db.delete(link)
    db.commit()
    return len(expired)