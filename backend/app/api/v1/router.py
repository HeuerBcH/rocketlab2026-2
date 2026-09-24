from fastapi import APIRouter

from app.auth.router import auth_router
from app.movies.router import genres_router, movies_router, people_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(movies_router, prefix="/movies", tags=["movies"])
api_router.include_router(genres_router, prefix="/genres", tags=["genres"])
api_router.include_router(people_router, prefix="/people", tags=["people"])
