from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, database, oauth2, utils


router = APIRouter(
    prefix="/api/topics",
    tags=["Topics"]
)


# Create topic
@router.post("/", status_code=status.HTTP_201_CREATED)
def create_topic(topic: schemas.TopicCreate, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    new_topic = models.Topic(user_id=current_user.id, **topic.dict())

    db.add(new_topic)
    db.commit()
    db.refresh(new_topic)

    return new_topic


# Get topics for a particular lesson
@router.get("/lesson/{id}", response_model=List[schemas.TopicGet])
def get_topics(id: int, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):

    topics = db.query(models.Topic).filter(
        models.Topic.lesson_id == id).all()

    return topics


# Get topic
@router.get("/{id}", response_model=schemas.TopicGet)
def get_topic(id: int, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    topic = db.query(models.Topic).filter(models.Topic.id == id).first()

    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Topic with id: {id} does not exist.")

    if topic.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return topic


# Update topic
@router.put("/", status_code=status.HTTP_200_OK)
def update_topic(updated_topic: schemas.TopicUpdate, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    topic_query = db.query(models.Topic).filter(
        models.Topic.id == updated_topic.id)
    topic = topic_query.first()

    course = db.query(models.Course).filter(
        models.Course.id == topic.course_id).first()

    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Topic with id: {updated_topic.id} does not exist.")

    if topic.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    # Calculate revision date, if it's a topic completion or revision
    if updated_topic.completed != topic.completed or updated_topic.revised != topic.revised:
        updated_topic.revision_date = utils.calculate_revision_date(
            updated_topic.revision_count, course.intensity)

    # Increase topic stability, if it's a topic completion or revision
    if updated_topic.completed != topic.completed or updated_topic.revised != topic.revised:
        updated_topic.stability = utils.increase_topic_stability(
            updated_topic.revision_count)

    topic_query.update(updated_topic.dict())
    db.commit()
    db.refresh(topic)

    return topic


# Delete topic
@router.delete("/{id}")
def delete_topic(id: int, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    topic_query = db.query(models.Topic).filter(models.Topic.id == id)
    topic = topic_query.first()

    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Topic with id:{id} does not exist.")

    if topic.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    topic_id = topic.id

    topic_query.delete(synchronize_session=False)
    db.commit()

    return topic_id
