from pathlib import Path
from datetime import datetime, date
from typing import List
from fastapi import APIRouter, status, HTTPException, Depends, Request, Header
from starlette.responses import JSONResponse
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from sqlalchemy.orm import Session
import razorpay

from .. import database, models, schemas, utils, oauth2
from ..config import mail, payment_settings


router = APIRouter(
    prefix="/api/users",
    tags=["Users"]
)


# FastAPI-Mail configuration
conf = ConnectionConfig(
    MAIL_USERNAME=mail.mail_username,
    MAIL_PASSWORD=mail.mail_password,
    MAIL_FROM=mail.mail_from,
    MAIL_PORT=mail.mail_port,
    MAIL_SERVER=mail.mail_server,
    MAIL_FROM_NAME=mail.mail_from_name,
    TEMPLATE_FOLDER=Path(__file__).parent / mail.template_folder,
    MAIL_TLS=mail.mail_tls,
    MAIL_SSL=mail.mail_ssl,
    USE_CREDENTIALS=mail.use_credentials,
    VALIDATE_CERTS=mail.validate_certs
)


# Create user
@router.post("/", status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):

    # Check if invite code exists in database
    invite = db.query(models.Invite).filter(
        models.Invite.invite_code == user.invite_code).first()

    if invite == None or invite.user_id != None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Wrong invite code.")

    # Username uniqueness check
    username = db.query(models.User).filter(
        models.User.username == user.username).first()
    if username != None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Username already exists.")

    # Email uniqueness check
    email = db.query(models.User).filter(
        models.User.email == user.email).first()
    if email != None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Email already registered.")

    # Password strength check
    if not utils.check_password_strength(user.password):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Password should be of at least 8 characters, and must contain at least one character and one digit.")

    # Hash password
    hashed_password = utils.hash(user.password)
    user.password = hashed_password

    # Add user
    new_user = models.User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    trial = True
    new_user.expiry_date = utils.calculate_expiry_date(new_user.creation_date, trial)
    invite.user_id = new_user.id
    db.commit()
    db.refresh(new_user)

    # Create access token
    access_token = oauth2.create_access_token(data={"id": new_user.id})

    return access_token


# Get user
@router.get("/", response_model=schemas.UserGet)
def get_user(db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    user = db.query(models.User).filter(
        models.User.id == current_user.id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id:{id} does not exist.")

    # Set inactive if expired
    if utils.check_expiry(user.expiry_date):
        user.active = False

    # Get user's courses to calculate user metrics
    courses = db.query(models.Course).filter(
        models.Course.user_id == current_user.id).all()

    # Calculate user goal status
    user.goal_status = utils.calculate_user_goal_status(courses)

    # Calculate user level
    user.level = utils.calculate_user_level(courses)

    # Calculate user strength
    user.strength = utils.calculate_user_strength(courses)

    # Calculate overall user progress
    user.progress = utils.calculate_user_progress(courses)

    db.commit()
    db.refresh(user)

    return user


# Update user data
@router.put("/", status_code=status.HTTP_200_OK)
def update_user(updated_user: schemas.UserUpdate, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    user_query = db.query(models.User).filter(
        models.User.id == current_user.id)
    user = user_query.first()

    # Username uniqueness check
    username = db.query(models.User).filter(
        models.User.username == updated_user.username).first()
    if updated_user.username != user.username and username != None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Username unavailable.")

    # Email uniqueness check
    email = db.query(models.User).filter(
        models.User.email == updated_user.email).first()
    if updated_user.email != user.email and email != None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Email already registered.")

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"User with id: {updated_user.id} does not exist.")

    user_query.update(updated_user.dict(), synchronize_session=False)
    db.commit()
    db.refresh(user)

    return user


# Update password
@router.post("/password")
def update_password(password: schemas.PasswordUpdate, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    user = db.query(models.User).filter(
        models.User.id == current_user.id).first()
    if not utils.verify(password.current_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong password. Please log out and reset your password, if you still face issues.")
    user.password = utils.hash(password.new_password)

    db.commit()
    db.refresh(user)

    return user


# Generate and mail password reset code
@router.post("/get-reset-code")
async def get_reset_code(requester: schemas.PasswordResetCode, db: Session = Depends(database.get_db)) -> JSONResponse:

    user = db.query(models.User).filter(
        models.User.email == requester.email[0]).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"User with email: {requester.email[0]} does not exist.")

    user.reset_code = utils.generate_secret_code(6)
    body = {
        "name": user.name,
        "code": user.reset_code
    }
    db.commit()

    message = MessageSchema(
        subject="Password Reset Initiated",
        recipients=requester.dict().get("email"),
        template_body=body
    )

    fm = FastMail(conf)
    await fm.send_message(message, template_name="password_reset.html")
    return JSONResponse(status_code=200, content={"message": "Password reset code sent to your registered email address."})


# Reset password with code
@router.post("/reset-password")
def reset_password(requester: schemas.PasswordReset, db: Session = Depends(database.get_db)) -> JSONResponse:

    user = db.query(models.User).filter(
        models.User.email == requester.email_address).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"User with email: {requester.email_address} does not exist.")

    if requester.reset_code != user.reset_code:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Wrong reset code. Access denied!")

    user.password = utils.hash(requester.new_password)

    db.commit()

    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Password reset successful."})


# Payment
@router.post("/payment")
def pay(local=Header(default=None)):
    global payment

    currency = "INR"
    amount = 99900

    if local != "INR":
        currency = "USD"
        amount = 1800

    client = razorpay.Client(
        auth=(payment_settings.razorpay_key_id, payment_settings.razorpay_key_secret))

    client.set_app_details({"title": "Kengram", "version": "0.1-beta"})

    data = {"amount": amount, "currency": currency}
    payment = client.order.create(data=data)
    return payment


# Renewal Payment
@router.post("/renewal-payment")
def pay(local=Header(default=None)):
    global payment

    currency = "INR"
    amount = 369900

    if local != "INR":
        currency = "USD"
        amount = 6600

    client = razorpay.Client(
        auth=(payment_settings.razorpay_key_id, payment_settings.razorpay_key_secret))

    client.set_app_details({"title": "Kengram", "version": "0.1-beta"})

    data = {"amount": amount, "currency": currency}
    payment = client.order.create(data=data)
    return payment


# Verify payment and send welcome package
@router.post("/verification")
async def verify(request: Request, x_razorpay_signature=Header(default=None),
                 x_razorpay_event_id=Header(default=None), db: Session = Depends(database.get_db)):

    # Handle duplicate webhook processing
    invites = db.query(models.Invite).filter(
        models.Invite.event_id == x_razorpay_event_id).first()
    if invites != None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Duplicate webhook request is being ignored!"
        )

    data = await request.json()
    body = await request.body()
    client = razorpay.Client(
        auth=(payment_settings.razorpay_key_id, payment_settings.razorpay_key_secret))

    # Verify webhook from Razorpay
    try:
        client.utility.verify_webhook_signature(
            body.decode("UTF-8"), x_razorpay_signature, payment_settings.razorpay_webhook_secret)
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied!")

    # Verify payment
    if data == None or payment == None:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                            detail="Payment gateway timed out. Please try again.")

    order_id = payment.get("id")
    payment_id = data.get("payload").get("payment").get("entity").get("id")
    generated_signature = utils.generate_signature(order_id, payment_id)
    params = {
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": generated_signature,
    }

    try:
        client.utility.verify_payment_signature(params)
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unable to verify payment!")

    # Check if registration or renewal
    user_email = data.get("payload").get("payment").get("entity").get("email")
    user = db.query(models.User).filter(
        models.User.email == user_email).first()

    # Handle renewal
    if user != None:
        invite = db.query(models.Invite).filter(
            models.Invite.email == user_email).first()

        # Set user to active
        user.active = True
        trial = False
        user.expiry_date = utils.calculate_expiry_date(
            datetime.now(), trial)

        # Set new event_id, date and invoice in invite
        invite.event_id = x_razorpay_event_id
        invite.invoice = "INV" + "_" + str(datetime.now().year) + str(
            datetime.now().month) + str(datetime.now().day) + "_" + str(invite.id)
        invite.creation_date = datetime.now().isoformat()

        db.commit()
        db.refresh(invite)
        db.refresh(user)

        # Send renewal mail
        email = []
        email.append(invite.email)
        purchase_timestamp = datetime.fromisoformat(
            str(invite.creation_date)).timestamp()
        purchase_date = date.fromtimestamp(purchase_timestamp)
        email_body = {
            "invoice": invite.invoice,
            "email": invite.email,
            "phone": invite.phone,
            "date": purchase_date,
        }
        message = MessageSchema(
            subject="Kengram Membership Renewal",
            recipients=email,
            template_body=email_body
        )

        fm = FastMail(conf)
        await fm.send_message(message, template_name="renewal.html")
        return JSONResponse(status_code=200, content={"message": "Membership renewed successfully, details sent to registered email address."})

    # Handle registration - Generate invite code
    invite_code = {
        "invite_code": utils.generate_secret_code(9),
        "phone": data.get("payload").get("payment").get("entity").get("contact"),
        "email": data.get("payload").get("payment").get("entity").get("email"),
        "event_id": x_razorpay_event_id
    }
    new_invite = models.Invite(**invite_code)

    db.add(new_invite)
    db.commit()
    db.refresh(new_invite)
    new_invite.invoice = "INV" + "_" + str(datetime.now().year) + str(
        datetime.now().month) + str(datetime.now().day) + "_" + str(new_invite.id)
    db.commit()

    # Welcome mail with welcome_package
    email = []
    email.append(new_invite.email)
    purchase_timestamp = datetime.fromisoformat(
        str(new_invite.creation_date)).timestamp()
    purchase_date = date.fromtimestamp(purchase_timestamp)
    invite_body = {
        "code": new_invite.invite_code,
        "invoice": new_invite.invoice,
        "email": new_invite.email,
        "phone": new_invite.phone,
        "date": purchase_date,
    }
    message = MessageSchema(
        subject="Welcome to Mastery Learning Challenge",
        recipients=email,
        template_body=invite_body
    )

    fm = FastMail(conf)
    await fm.send_message(message, template_name="welcome_package.html")
    return JSONResponse(status_code=200, content={"message": "Welcome package successfully sent to registered email address."})


# Sudo get all users
@router.get("/all", response_model=List[schemas.UserGet])
def get_all_users(db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    sudo = db.query(models.User).filter(
        models.User.id == current_user.id).first()
    if not sudo.superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied!")
    users = db.query(models.User).all()
    return users


# Sudo create invite code
@router.post("/create-invite")
async def create_invite_code(invite: schemas.InviteCreate, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    sudo = db.query(models.User).filter(
        models.User.id == current_user.id).first()
    if not sudo.superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied!")

    # Handle registration - Generate invite code
    invite_code = {
        "invite_code": utils.generate_secret_code(9),
        "phone": invite.phone,
        "email": invite.email,
        "event_id": "SUDO",
        "invoice": "FREE"
    }
    new_invite = models.Invite(**invite_code)

    db.add(new_invite)
    db.commit()
    db.refresh(new_invite)

    # Welcome mail with welcome_package
    email = []
    email.append(new_invite.email)
    purchase_timestamp = datetime.fromisoformat(
        str(new_invite.creation_date)).timestamp()
    purchase_date = date.fromtimestamp(purchase_timestamp)
    invite_body = {
        "code": new_invite.invite_code,
        "invoice": new_invite.invoice,
        "email": new_invite.email,
        "phone": new_invite.phone,
        "date": purchase_date,
    }
    message = MessageSchema(
        subject="Welcome to Kengram Insiders",
        recipients=email,
        template_body=invite_body
    )

    fm = FastMail(conf)
    await fm.send_message(message, template_name="welcome_package.html")
    return JSONResponse(status_code=200, content={"message": "Welcome package successfully sent to registered email address."})


# Sudo renew membership
@router.post("/renew")
async def renew_membership(learner: schemas.UserManage, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    sudo = db.query(models.User).filter(
        models.User.id == current_user.id).first()
    if not sudo.superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied!")

    user = db.query(models.User).filter(
        models.User.id == learner.id).first()

    if user == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"User with id: {id} does not exist")

    # Set user to active
    user.active = True
    trial = False
    user.expiry_date = utils.calculate_expiry_date(
        datetime.now(), trial)

    db.commit()
    db.refresh(user)

    return user

# Sudo delete user
@router.delete("/{id}")
def delete_user(id: int, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    sudo = db.query(models.User).filter(
        models.User.id == current_user.id).first()
    if not sudo.superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied!")

    user_query = db.query(models.User).filter(models.User.id == id)
    user = user_query.first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"User with id: {id} does not exist.")

    user_id = user.id

    user_query.delete(synchronize_session=False)
    db.commit()

    return user_id


# Sudo get user's courses
@router.get("/courses/{id}", response_model=List[schemas.CourseGet])
def get_user_courses(id: int, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    sudo = db.query(models.User).filter(
        models.User.id == current_user.id).first()
    if not sudo.superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied!")

    courses = db.query(models.Course).filter(
        models.Course.user_id == id).all()

    return courses


# Sudo get user's lessons
@router.get("/lessons/{id}", response_model=List[schemas.LessonGet])
def get_user_lessons(id: int, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    sudo = db.query(models.User).filter(
        models.User.id == current_user.id).first()
    if not sudo.superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied!")

    lessons = db.query(models.Lesson).filter(
        models.Lesson.user_id == id).all()

    return lessons


# Sudo get user's topics
@router.get("/topics/{id}", response_model=List[schemas.TopicGet])
def get_user_topics(id: int, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    sudo = db.query(models.User).filter(
        models.User.id == current_user.id).first()
    if not sudo.superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied!")

    topics = db.query(models.Topic).filter(
        models.Topic.user_id == id).all()

    return topics


# Sudo get user's bursts
@router.get("/bursts/{id}", response_model=List[schemas.BurstGet])
def get_user_bursts(id: int, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    sudo = db.query(models.User).filter(
        models.User.id == current_user.id).first()
    if not sudo.superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied!")

    bursts = db.query(models.Burst).filter(
        models.Burst.user_id == id).all()

    return bursts


# Sudo make/unmake superuser
@router.post("/sudo")
def sudo_user(learner: schemas.UserManage, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    sudo = db.query(models.User).filter(
        models.User.id == current_user.id).first()
    if not sudo.superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied!")

    user = db.query(models.User).filter(models.User.id == learner.id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"User with id: {id} does not exist.")

    user.superuser = not user.superuser
    db.commit()
    db.refresh(user)

    return user
