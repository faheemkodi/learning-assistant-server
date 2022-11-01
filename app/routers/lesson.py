from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, database, oauth2, utils


router = APIRouter(
    prefix="/api/lessons",
    tags=["Lessons"]
)


# Create lesson
@router.post("/", status_code=status.HTTP_201_CREATED)
def create_lesson(lesson: schemas.LessonCreate, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    new_lesson = models.Lesson(user_id=current_user.id, **lesson.dict())

    db.add(new_lesson)
    db.commit()
    db.refresh(new_lesson)

    return new_lesson


# Get all lessons of a particular course
@router.get("/course/{id}", response_model=List[schemas.LessonGet])
def get_lessons(id: int, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):

    lessons = db.query(models.Lesson).filter(
        models.Lesson.course_id == id).all()

    for lesson in lessons:
        # Get topics to calculate lesson metrics
        topics = db.query(models.Topic).filter(
            models.Topic.lesson_id == lesson.id).all()

        completed_topics = list(
            filter(lambda topic: topic.completed == True, topics))

        # Calculate overall lesson progress
        lesson.progress = utils.calculate_overall_progress(topics)

        # Calculate overall lesson stability
        lesson.stability = utils.calculate_overall_stability(completed_topics)

    db.commit()
    for lesson in lessons:
        db.refresh(lesson)

    return lessons


# Get single lesson
@router.get("/{id}", response_model=schemas.LessonGet)
def get_lesson(id: int, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    lesson = db.query(models.Lesson).filter(models.Lesson.id == id).first()

    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Lesson with id: {id} does not exist.")

    if lesson.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    # Get topics to calculate lesson metrics
    topics = db.query(models.Topic).filter(models.Topic.lesson_id == id).all()
    completed_topics = list(
        filter(lambda topic: topic.completed == True, topics))

    # Calculate overall lesson progress
    lesson.progress = utils.calculate_overall_progress(topics)

    # Calculate overall lesson stability
    lesson.stability = utils.calculate_overall_stability(completed_topics)

    db.commit()
    db.refresh(lesson)

    return lesson


# Update lesson
@router.put("/", status_code=status.HTTP_200_OK)
def update_lesson(updated_lesson: schemas.LessonUpdate, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    lesson_query = db.query(models.Lesson).filter(
        models.Lesson.id == updated_lesson.id)
    lesson = lesson_query.first()

    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Lesson with id: {updated_lesson.id} does not exist")

    if lesson.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    lesson_query.update(updated_lesson.dict())
    db.commit()
    db.refresh(lesson)

    return lesson


# Delete lesson
@router.delete("/{id}")
def delete_lesson(id: int, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    lesson_query = db.query(models.Lesson).filter(models.Lesson.id == id)
    lesson = lesson_query.first()

    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Lesson with id: {id} does not exist.")

    if lesson.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    lesson_id = lesson.id

    lesson_query.delete(synchronize_session=False)
    db.commit()

    return lesson_id
