from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

from .. import database, models, schemas, oauth2, utils


router = APIRouter(
    prefix="/api/courses",
    tags=["Courses"]
)


# Create course
@router.post("/", status_code=status.HTTP_201_CREATED)
def create_course(course: schemas.CourseCreate, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    new_course = models.Course(user_id=current_user.id, **course.dict())
    new_course.goal_reset_date = utils.calculate_goal_reset_date(
        datetime.now().astimezone())
    db.add(new_course)
    db.commit()
    db.refresh(new_course)

    return new_course


# Get single course
@router.get("/{id}", response_model=schemas.CourseGet)
def get_course(id: int, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    course = db.query(models.Course).filter(models.Course.id == id).first()

    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Course with id:{id} does not exist")
    if course.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Get bursts to calculate course metrics
    course_bursts = db.query(models.Burst).filter(
        models.Burst.course_id == id).all()

    # Check and reset course streak
    if utils.reset_course_streak(course_bursts):
        course.streak = 0

    # Calculate course strength
    course.strength = utils.calculate_course_strength(course_bursts)

    topics = db.query(models.Topic).filter(models.Topic.course_id == id).all()
    completed_topics = list(
        filter(lambda topic: topic.completed == True, topics))

    # Calculate overall course progress
    course.progress = utils.calculate_overall_progress(topics)

    # Calculate overall course stability
    course.stability = utils.calculate_overall_stability(completed_topics)

    # Calculate current course velocity
    if course.progress < 100:
        course.current_velocity = utils.calculate_current_velocity(
            course.creation_date, course.progress)

    # Calculate required course velocity
    course.required_velocity = utils.calculate_required_velocity(
        course.deadline, course.progress)

    db.commit()
    db.refresh(course)

    return course


# Get all courses for current user
@router.get("/", response_model=List[schemas.CourseGet])
def get_courses(db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    courses = db.query(models.Course).filter(
        models.Course.user_id == current_user.id).all()

    for course in courses:
        # Get bursts to calculate course goal
        course_bursts = db.query(models.Burst).filter(
            models.Burst.course_id == course.id).all()

        # Calculate course goal reset date
        if datetime.now().timestamp() > course.goal_reset_date.timestamp():
            course.goal_reset_date = utils.calculate_goal_reset_date(
                course.goal_reset_date)
            course.goal_status = 0

        # Calculate course goal status
        course.goal_status = utils.calculate_goal_status(course_bursts, course)

        # Get topics to calculate topic metrics
        topics = db.query(models.Topic).filter(
            models.Topic.course_id == course.id).all()

        # Set revision due, check revision overdue and decrease stability
        for topic in topics:
            if topic.revision_date != None and topic.revised == True and utils.revision_due(topic.revision_date):
                topic.revised = False
            if topic.revision_date != None and not topic.revised and utils.revision_overdue(topic.revision_date):
                topic.stability = utils.decrease_topic_stability(
                    topic.stability, topic.revision_count, topic.revision_date)
                topic.revision_date = utils.calculate_revision_date(
                    topic.revision_count, course.intensity)

    db.commit()
    for course in courses:
        db.refresh(course)

    return courses


# Update course
@router.put("/", status_code=status.HTTP_200_OK)
def update_course(updated_course: schemas.CourseUpdate, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    course_query = db.query(models.Course).filter(
        models.Course.id == updated_course.id)
    course = course_query.first()

    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Course with id: {updated_course.id} does not exist.")
    if course.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    course_query.update(updated_course.dict(), synchronize_session=False)
    db.commit()
    db.refresh(course)

    return course


# Delete course
@router.delete("/{id}")
def delete_course(id: int, db: Session = Depends(database.get_db), current_user=Depends(oauth2.get_current_user)):
    course_query = db.query(models.Course).filter(models.Course.id == id)
    course = course_query.first()

    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Course with id: {id} does not exist.")

    if course.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    course_id = course.id

    course_query.delete(synchronize_session=False)
    db.commit()

    return course_id
