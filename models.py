from sqlalchemy import Column, Integer, String,  Date, ForeignKey
from database import Base, engine
from sqlalchemy.orm import relationship

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(150), nullable=False)
    last_name = Column(String(150),  nullable=False)
    email = Column(String(150), nullable=False, unique=True, index=True)
    phone_number = Column(String(50), nullable=True)
    birthday = Column(Date, nullable=False)
    additional_info = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id")) 

    user = relationship("User", back_populates="contacts")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(150), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    refresh_token = Column(String(255), nullable=True)

    contacts = relationship("Contact", back_populates="user") 


Base.metadata.create_all(bind=engine)