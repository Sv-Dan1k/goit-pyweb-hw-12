from datetime import  datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Path, Query, Security
from fastapi.security import OAuth2PasswordRequestForm, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text, extract, or_, and_
from sqlalchemy.orm import Session
from models import Contact, User
from schemas import ContactSchema, ContactResponse, UserModel
from pydantic import BaseModel

from auth import create_access_token, create_refresh_token, get_email_form_refresh_token, get_current_user, Hash
from database import get_db


app = FastAPI()
hash_handler = Hash()
security = HTTPBearer()

    
@app.post("/signup", tags=["auth"])
async def signup(body: UserModel, db: Session = Depends(get_db)):
    exist_user = db.query(User).filter(User.email == body.username).first()
    if exist_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")
    new_user = User(email=body.username, password=hash_handler.get_password_hash(body.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"new_user": new_user.email}


@app.post("/login", tags=["auth"])
async def login(body: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email")
    if not hash_handler.verify_password(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    access_token = await create_access_token(data={"sub": user.email})
    refresh_token = await create_refresh_token(data={"sub": user.email})
    user.refresh_token = refresh_token
    db.commit()
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@app.get('/refresh_token', tags=["auth"])
async def refresh_token(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    email = await get_email_form_refresh_token(token)
    user = db.query(User).filter(User.email == email).first()
    if user.refresh_token != token:
        user.refresh_token = None
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = await create_access_token(data={"sub": email})
    refresh_token = await create_refresh_token(data={"sub": email})
    user.refresh_token = refresh_token
    db.commit()
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@app.get("/secret", tags=["auth"])
async def read_item(current_user: User = Depends(get_current_user)):
    return {"message": 'secret router', "owner": current_user.email}

@app.get("/api/healthchecker")
def healthchecker(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT 1")).fetchone()
        if result is None:
            raise HTTPException(
                status_code=500, detail="Database is not configured correctly"
            )
        return {"message": "Welcome to FastAPI!"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error connecting to the database")


@app.get("/")
def main_root():
    return {"message": "Hello world"}


@app.get("/contacts", response_model=list[ContactResponse], tags=["contacts"])
def get_contacts(
    current_user: User = Depends(get_current_user), 
    first_name: Optional[str] = Query(None, title="First Name"),
    last_name: Optional[str] = Query(None, title="Last Name"),
    email: Optional[str] = Query(None, title="Email"),
    db: Session = Depends(get_db),
):
    # query = db.query(Contact.user_id == current_user.id)
    query = db.query(Contact).filter(Contact.user_id == current_user.id)

    if first_name:
        query = query.filter(Contact.first_name.ilike(f"%{first_name}%"))
    if last_name:
        query = query.filter(Contact.last_name.ilike(f"%{last_name}%"))
    if email:
        query = query.filter(Contact.email.ilike(f"%{email}%"))

    contacts = query.all()
    return contacts


@app.get("/contacts/{contact_id}", response_model=ContactResponse, tags=["contacts"])
async def get_contact_by_id(
    contact_id: int = Path(ge=1), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    contact = db.query(Contact).filter_by(id=contact_id).first()
    #contact = db.query(Contact).filter_by(id=contact_id, user_id=current_user.id).first()
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT FOUND")
    return contact


@app.post("/contacts", response_model=ContactResponse, tags=["contacts"])
async def create_contact(body: ContactSchema, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contact = db.query(Contact).filter_by(email=body.email).first()
    if contact:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Contact already exists!"
        )

    contact = Contact(**body.model_dump(),user_id=current_user.id) 
    db.add(contact)
    db.commit()
    return contact


@app.put("/contacts/{contact_id}", response_model=ContactResponse, tags=["contacts"])
async def update_contact(
    body: ContactSchema, contact_id: int = Path(ge=1), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    # contact = db.query(Contact).filter_by(id=contact_id, user_id=current_user.id).first()
    contact = db.query(Contact).filter_by(id=contact_id, user_id=current_user.id).first()
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    contact.first_name = body.first_name
    contact.last_name = body.last_name
    contact.email = body.email
    contact.phone_number = body.phone_number
    contact.birthday = body.birthday
    contact.additional_info = body.additional_info

    db.commit()
    return contact


@app.delete("/contacts/{contact_id}", response_model=ContactResponse, tags=["contacts"])
async def delete_contact(contact_id: int = Path(ge=1), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contact = db.query(Contact).filter_by(id=contact_id, user_id=current_user.id).first()
    
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT FOUND")

    db.delete(contact)
    db.commit()
    return contact


@app.get(
    "/contacts/upcoming-birthdays/",
    response_model=List[ContactResponse],
    tags=["contacts"],
)
def get_upcoming_birthdays(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = datetime.now().date()
    end_date = today + timedelta(days=7)

    if today.month == 12 and end_date.month == 1:
        contacts = (
            db.query(Contact)
            .filter(
                or_(
                    extract("month", Contact.birthday) == today.month,
                    extract("day", Contact.birthday) >= today.day,
                    extract("month", Contact.birthday) == end_date.month,
                    extract("day", Contact.birthday) <= end_date.day,
                )
            )
            .filter(Contact.user_id == current_user.id)
            .all()
        )
    else:
        contacts = (
            db.query(Contact)
            .filter(
                or_(
                    and_(
                        extract("month", Contact.birthday) == today.month,
                        extract("day", Contact.birthday) >= today.day,
                    ),
                    and_(
                        extract("month", Contact.birthday) == end_date.month,
                        extract("day", Contact.birthday) <= end_date.day,
                    ),
                )
            )
            .filter(Contact.user_id == current_user.id)
            .all()
        )

    return contacts




