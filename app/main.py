from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import user, auth, course, lesson, topic, burst


# Initiating FastAPI instance
app = FastAPI()


# Setting CORS middleware
origins = [
    "https://www.kengram.com",
    "https://kengram.com",
    "https://kengram.netlify.app",
    "https://52.66.76.174:0"
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# Including routers
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(course.router)
app.include_router(lesson.router)
app.include_router(topic.router)
app.include_router(burst.router)


@app.get("/")
async def root():
    return {"message": "Kengram API is running smoothly!"}


@app.post("/")
async def root():
    return {"message": "Kengram API is running smoothly!"}
