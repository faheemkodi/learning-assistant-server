from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from .. import database, models, schemas, utils, oauth2

router = APIRouter(
    prefix="/api/bursts",
    tags=["Bursts"]
)


# Create burst
@router.post("/", status_code=status.HTTP_201_CREATED)
def create_burst(burst: schemas.BurstCreate, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    new_burst = models.Burst(user_id=current_user.id, **burst.dict())
    course = db.query(models.Course).filter(
        models.Course.id == new_burst.course_id).first()

    # Get bursts to calculate course metrics
    course_bursts = db.query(models.Burst).filter(
        models.Burst.course_id == new_burst.course_id).all()

    # Check and increment streak
    if utils.increment_course_streak(course_bursts):
        course.streak += 1

    db.add(new_burst)
    db.commit()
    db.refresh(new_burst)

    return new_burst


# Get burst interruptions data for a particular user
@router.get("/interruptions")
def get_interruptions(db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    bursts = db.query(models.Burst).filter(
        models.Burst.user_id == current_user.id).all()

    self_interrupted = 0
    digital_interrupted = 0
    people_interrupted = 0
    uninterrupted = 0

    for burst in bursts:
        if not burst.interrupted:
            uninterrupted += 1
        else:
            if burst.interruption == "Self":
                self_interrupted += 1
            elif burst.interruption == "Digital":
                digital_interrupted += 1
            elif burst.interruption == "People":
                people_interrupted += 1

    data = [
        {"name": "Self", "value": self_interrupted},
        {"name": "Digital", "value": digital_interrupted},
        {"name": "People", "value": people_interrupted},
        {"name": "Uninterrupted", "value": uninterrupted}
    ]

    return data
