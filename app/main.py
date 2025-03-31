from fastapi import FastAPI, HTTPException, Depends, status, Request, Query, Security
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from . import models, schemas, crud, auth
from .database import SessionLocal, engine
from datetime import datetime

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Вспомогательная функция для необязательной аутентификации
def get_current_user_optional(token: str = Depends(auth.oauth2_scheme)):
    try:
        return auth.get_current_user(token)
    except HTTPException:
        return None

# Регистрация и аутентификация
@app.post("/register", response_model=schemas.User)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

@app.post("/token", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# Создание ссылки (доступно всем)
optional_auth = HTTPBearer(auto_error=False)

@app.post("/links/shorten", response_model=schemas.Link)
async def create_short_link(
    link: schemas.LinkCreate,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(optional_auth)
):
    user = None
    if credentials:
        try:
            user = await auth.get_current_user(credentials.credentials)
        except:
            pass
    
    try:
        return crud.create_link_with_alias(
            db=db,
            link=link,
            user_id=user.id if user else None
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Обновление/удаление (только для авторизованных)
@app.put("/links/{short_code}", response_model=schemas.Link)
def update_link(
    short_code: str, 
    link_update: schemas.LinkUpdate, 
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_user)
):
    try:
        return crud.update_link(db, short_code=short_code, link_update=link_update, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@app.delete("/links/{short_code}")
def delete_short_link(
    short_code: str, 
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_user)
):
    if not crud.delete_link(db, short_code=short_code, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="Link not found")
    return {"message": "Link deleted successfully"}

@app.get("/{short_code}")
def redirect_to_original(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    db_link = crud.get_link_by_short_code(db, short_code=short_code)
    if not db_link or not db_link.is_active:
        raise HTTPException(status_code=404, detail="Link not found or inactive")
    
    db_link.clicks += 1
    db_link.last_accessed_at = datetime.now()
    db.commit()
    db.refresh(db_link)
    
    return RedirectResponse(url=db_link.original_url)
    
@app.get("/links/{short_code}/stats", response_model=schemas.LinkStats)
def get_link_stats(
    short_code: str,
    db: Session = Depends(get_db)
):
    stats = crud.get_link_stats(db, short_code=short_code)
    if not stats:
        raise HTTPException(status_code=404, detail="Link not found")
    return stats

@app.get("/links/search/", response_model=list[schemas.LinkSearchResult])
def search_links(
    original_url: str = Query(..., min_length=3),
    db: Session = Depends(get_db)
):
    links = crud.search_links(db, original_url=original_url)
    return links

@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    crud.delete_expired_links(db)
    db.close()