from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.database import engine, Base

app = FastAPI(title="招标信息管理系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    # Import all models so Base knows about them
    from .models import (  # noqa: F401
        user, organization, platform, manager,
        project, bidding_info, bid_info, bid_result, operation_log,
    )
    Base.metadata.create_all(bind=engine)

    # Create default admin user
    from sqlalchemy.orm import Session
    from .models.user import User
    from .core.security import get_password_hash

    db = Session(bind=engine)
    try:
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                display_name="管理员",
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print("Default admin user created: admin / admin123")
    finally:
        db.close()


# Register routes
from .api.auth import router as auth_router
from .api.users import router as users_router
from .api.stats import router as stats_router
from .api.logs import router as logs_router
from .api.organizations import router as orgs_router
from .api.platforms import router as platforms_router
from .api.managers import router as managers_router

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(stats_router)
app.include_router(logs_router)
app.include_router(orgs_router)
app.include_router(platforms_router)
app.include_router(managers_router)

# Bidding management routers
from .api.projects import router as projects_router
from .api.bidding_infos import router as biddings_router
from .api.bid_infos import router as bids_router
from .api.bid_results import router as results_router

app.include_router(projects_router)
app.include_router(biddings_router)
app.include_router(bids_router)
app.include_router(results_router)
