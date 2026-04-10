from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, inspect as sa_inspect

from .core.database import engine, Base

app = FastAPI(title="招标信息管理系统", version="2.0.0")

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
        project, operation_log,
    )
    Base.metadata.create_all(bind=engine)

    # Auto-migrate: add org_type column if not exists
    inspector = sa_inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('organizations')]
    if 'org_type' not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE organizations ADD COLUMN org_type VARCHAR(10) DEFAULT 'external'"))
            conn.commit()
        print("Migration: added org_type column to organizations")

    # Auto-migrate: add winning_org_ids column to project_infos if not exists
    proj_columns = [col['name'] for col in inspector.get_columns('project_infos')]
    if 'winning_org_ids' not in proj_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE project_infos ADD COLUMN winning_org_ids JSON DEFAULT '[]'"))
            conn.commit()
        print("Migration: added winning_org_ids column to project_infos")

    # Auto-migrate: add is_consortium_lead column to project_infos if not exists
    if 'is_consortium_lead' not in proj_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE project_infos ADD COLUMN is_consortium_lead BOOLEAN DEFAULT 1"))
            conn.commit()
        print("Migration: added is_consortium_lead column to project_infos")

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

        # Ensure our company exists in organizations table (ID=1)
        from .models.organization import Organization, OrgType
        our_company_name = "浙江意诚检测有限公司"
        existing = db.query(Organization).filter(
            (Organization.name == our_company_name) | (Organization.id == 1)
        ).first()
        if existing:
            # Ensure org_type is ours
            if existing.org_type != OrgType.ours:
                existing.org_type = OrgType.ours
                db.commit()
                print(f"Updated organization org_type: {our_company_name} -> ours")
        else:
            our_org = Organization(
                id=1,
                name=our_company_name,
                short_name="意诚检测",
                contact_person="",
                contact_phone="",
                notes="我方公司",
                org_type="ours",
            )
            db.add(our_org)
            db.commit()
            print(f"Default organization created: {our_company_name} (ID=1)")
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
from .api.projects import router as projects_router

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(stats_router)
app.include_router(logs_router)
app.include_router(orgs_router)
app.include_router(platforms_router)
app.include_router(managers_router)
app.include_router(projects_router)
