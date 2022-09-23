from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from .. import database, models, utils, oauth2


router = APIRouter(tags=["Authentication"])


@router.post("/api/login")
def login(credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):

    user = db.query(models.User).filter(
        models.User.username == credentials.username).first()

    if not user:
        user = db.query(models.User).filter(
            models.User.email == credentials.username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Please ensure the username and password you've entered is correct.")

    if not utils.verify(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Please ensure the username and password you've entered is correct.")

    # Create access token
    access_token = oauth2.create_access_token(data={"id": user.id})

    return access_token
