from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, mails, groups, templates, contacts, admin, ws

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(mails.router, prefix="/mails", tags=["mails"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(contacts.router, prefix="/users", tags=["contacts"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(ws.router, tags=["realtime"])
