from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import user, auth, course, lesson, topic, burst


# Initiating FastAPI instance
app = FastAPI()


# Setting CORS middleware
origins = [
    "http://localhost:3000",
    "localhost:3000",
    "http://192.168.0.113:3000",
    "192.168.0.113:3000",
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
