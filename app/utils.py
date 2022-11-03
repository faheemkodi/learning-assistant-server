import requests
import secrets
import string
import hmac
import hashlib
from math import floor
from datetime import datetime, date
from typing import List
from passlib.context import CryptContext

from .config import payment_settings


# Set passlib hashing algorithm to bcrypt
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash(password: str):
    return password_context.hash(password)


def verify(plain, hashed):
    return password_context.verify(plain, hashed)


def calculate_expiry_date(date, trial):
    year_in_seconds = 31536000
    three_months_in_seconds = 7776000

    if trial == True:
        new_date = datetime.fromtimestamp(date.timestamp() + three_months_in_seconds)
        return new_date
        
    new_date = datetime.fromtimestamp(date.timestamp() + year_in_seconds)
    return new_date


def check_expiry(date):
    if datetime.now().timestamp() > date.timestamp():
        return True
    return False


def check_password_strength(password: str):
    length = len(password)
    if length < 8:
        return False
    letters = False
    numbers = False
    for character in password:
        if character.isalpha():
            letters = True
        elif character.isdigit():
            numbers = True
        if numbers and letters:
            return True
    return False


def increment_course_streak(bursts: List):
    today = date.today()
    burst_count_today = 0
    for burst in bursts:
        if datetime.fromisoformat(str(burst.creation_date)).date() == today:
            burst_count_today += 1
    if burst_count_today == 0:
        return True
    return False


def reset_course_streak(bursts: List):
    now = datetime.now().timestamp()
    day_in_seconds = 86400
    last_burst_time = 0
    for burst in bursts:
        if burst.creation_date.timestamp() > last_burst_time:
            last_burst_time = burst.creation_date.timestamp()
    if len(bursts) > 0 and now - last_burst_time > day_in_seconds:
        return True
    return False


def calculate_course_strength(bursts: List):
    duration = 0
    for burst in bursts:
        duration += burst.duration
    return floor(duration / 60)


def calculate_goal_reset_date(date):
    week_in_seconds = 604800
    new_date = datetime.fromtimestamp(date.timestamp() + week_in_seconds)
    return new_date


def calculate_goal_status(bursts: List, course):
    goal_achieved = 0
    goal_target = course.goal * 60
    week_in_seconds = 604800
    start_date = course.goal_reset_date.timestamp() - week_in_seconds
    end_date = course.goal_reset_date.timestamp()
    for burst in bursts:
        if burst.creation_date.timestamp() > start_date and burst.creation_date.timestamp() < end_date:
            goal_achieved += burst.duration
    goal_status = (goal_achieved / goal_target) * 100
    return goal_status


def calculate_revision_date(revision_count, intensity):
    day_in_seconds = 86400
    date = datetime.now().timestamp()
    if revision_count == 0:
        date += day_in_seconds
    else:
        if intensity == "Low":
            date += day_in_seconds * revision_count * 9
        elif intensity == "High":
            date += day_in_seconds * revision_count * 3
        else:
            date += day_in_seconds * revision_count * 6
    new_date = datetime.fromtimestamp(date)
    return new_date


def revision_due(date):
    now = datetime.now().timestamp()
    due_date = date.timestamp()
    if now > due_date:
        return True
    return False


def revision_overdue(date):
    day_in_seconds = 86400
    now = datetime.now().timestamp()
    overdue_date = date.timestamp() + day_in_seconds
    if now > overdue_date:
        return True
    return False


def increase_topic_stability(stability):
    new_stability = round(stability + 20)
    if new_stability > 100:
        return 100
    return new_stability


def decrease_topic_stability(stability, revision_count, revision_date):
    day_in_seconds = 86400
    date = datetime.now().timestamp()
    days_elapsed = floor((date - revision_date.timestamp()) / day_in_seconds)
    if revision_count == 0:
        new_stability = stability - (10 * days_elapsed)
    else:
        new_stability = round(
            stability - ((10 * days_elapsed) / revision_count))
    if new_stability < 0:
        return 0
    return new_stability


def calculate_overall_progress(units):
    if len(units) > 0:
        completed_units = 0
        for unit in units:
            if unit.completed:
                completed_units += 1
        overall_progress = round((completed_units / len(units)) * 100)
        return overall_progress
    else:
        return 0


def calculate_overall_stability(units):
    if len(units) > 0:
        stability_sum = 0
        for unit in units:
            stability_sum += unit.stability
        overall_stability = round(stability_sum / len(units))
        return overall_stability
    else:
        return 0


def calculate_current_velocity(creation_date, progress):
    week_in_seconds = 604800
    now = datetime.now().timestamp()
    start_date = creation_date.timestamp()
    weeks_elapsed = round((now - start_date) / week_in_seconds)
    if weeks_elapsed > 0:
        current_velocity = floor(progress / weeks_elapsed)
        return current_velocity
    else:
        return 0


def calculate_required_velocity(deadline, progress):
    week_in_seconds = 604800
    now = datetime.now().timestamp()
    deadline_date = deadline.timestamp()
    number_of_weeks = floor((deadline_date - now) / week_in_seconds)
    if number_of_weeks < 1:
        return 100
    required_velocity = round((100 - progress) / number_of_weeks)
    return required_velocity


def calculate_user_goal_status(courses):
    if len(courses) > 0:
        goal_sum = 0
        goal_status_sum = 0
        for course in courses:
            goal_sum += course.goal
            goal_status_sum += (course.goal_status * course.goal) / 100
        user_goal_status = round((goal_status_sum / goal_sum) * 100)
        if user_goal_status > 100:
            return 100
        return user_goal_status
    else:
        return 0


def calculate_user_level(courses):
    if len(courses) > 0:
        overall_strength = 0
        for course in courses:
            overall_strength += course.strength
        user_level = floor(overall_strength / 10)
        return user_level
    else:
        return 0


def calculate_user_strength(courses):
    if len(courses) > 0:
        overall_strength = 0
        for course in courses:
            overall_strength += course.strength
        return overall_strength
    else:
        return 0


def calculate_user_progress(courses):
    length = len(courses)
    if length > 0:
        progress_sum = 0
        for course in courses:
            progress_sum += course.progress
        overall_progress = floor(progress_sum / length)
        if overall_progress > 100:
            return 100
        return overall_progress
    else:
        return 0


def generate_secret_code(length: int):
    code = "".join(secrets.choice(string.ascii_letters + string.digits)
                   for i in range(length))
    return code


def generate_signature(oid, pid):
    signature = hmac.new(payment_settings.razorpay_key_secret.encode(),
                         digestmod=hashlib.sha256)
    symbol = "|"
    signature.update(oid.encode() + symbol.encode() + pid.encode())
    return signature.hexdigest()
