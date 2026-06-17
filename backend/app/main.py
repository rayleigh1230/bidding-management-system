from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, inspect as sa_inspect
from datetime import datetime

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
        project, operation_log, scrape,
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

    # Auto-migrate: add parent_project_id column to project_infos if not exists
    if 'parent_project_id' not in proj_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE project_infos ADD COLUMN parent_project_id INTEGER REFERENCES project_infos(id)"))
            conn.commit()
        print("Migration: added parent_project_id column to project_infos")

    # Auto-migrate: add is_bid_failed column to project_infos if not exists
    proj_columns = [col['name'] for col in inspector.get_columns('project_infos')]
    if 'is_bid_failed' not in proj_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE project_infos ADD COLUMN is_bid_failed BOOLEAN DEFAULT 0"))
            conn.commit()
        print("Migration: added is_bid_failed column to project_infos")

    # Auto-migrate: add is_multi_lot column to project_infos if not exists
    proj_columns = [col['name'] for col in inspector.get_columns('project_infos')]
    if 'is_multi_lot' not in proj_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE project_infos ADD COLUMN is_multi_lot BOOLEAN DEFAULT 0"))
            conn.commit()
        print("Migration: added is_multi_lot column to project_infos")

    # Auto-migrate: add result_documents column to project_infos if not exists
    proj_columns = [col['name'] for col in inspector.get_columns('project_infos')]
    if 'result_documents' not in proj_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE project_infos ADD COLUMN result_documents JSON DEFAULT '[]'"))
            conn.commit()
        print("Migration: added result_documents column to project_infos")

    # Auto-migrate: add external_no/source/source_url columns to project_infos
    proj_columns = [col['name'] for col in inspector.get_columns('project_infos')]
    if 'external_no' not in proj_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE project_infos ADD COLUMN external_no VARCHAR(100)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_project_external_no ON project_infos(external_no)"))
            conn.commit()
        print("Migration: added external_no column to project_infos")
    if 'source' not in proj_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE project_infos ADD COLUMN source VARCHAR(50) DEFAULT 'manual'"))
            conn.commit()
        print("Migration: added source column to project_infos")
    if 'source_url' not in proj_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE project_infos ADD COLUMN source_url VARCHAR(500) DEFAULT ''"))
            conn.commit()
        print("Migration: added source_url column to project_infos")

    # Auto-migrate: add abandon_notes column to project_infos if not exists
    proj_columns = [col['name'] for col in inspector.get_columns('project_infos')]
    if 'abandon_notes' not in proj_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE project_infos ADD COLUMN abandon_notes TEXT DEFAULT ''"))
            conn.commit()
        print("Migration: added abandon_notes column to project_infos")

    # Cleanup orphan scrape runs from previous unclean shutdown
    from sqlalchemy.orm import Session as _Session
    from .models.scrape import ScrapeRun as _ScrapeRun
    _cleanup_db = _Session(bind=engine)
    try:
        _orphans = _cleanup_db.query(_ScrapeRun).filter(
            _ScrapeRun.status == "running",
            _ScrapeRun.finished_at.is_(None),
        ).all()
        for _orphan in _orphans:
            _orphan.status = "failed"
            _orphan.error_summary = {"system": "服务重启中断"}
            _orphan.finished_at = datetime.now()
        if _orphans:
            _cleanup_db.commit()
            print(f"Cleanup: marked {len(_orphans)} orphan scrape run(s) as failed")
    finally:
        _cleanup_db.close()

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

        # Upgrade 3 bid specialists' role to bid_specialist (idempotent)
        from .models.user import UserRole as _UserRole
        SPECIALIST_NAMES = ["倪敏", "刘阳莉", "施艳荷"]
        specialists = db.query(User).filter(User.display_name.in_(SPECIALIST_NAMES)).all()
        upgraded = 0
        for u in specialists:
            role_val = u.role.value if hasattr(u.role, 'value') else str(u.role)
            if role_val != "bid_specialist":
                u.role = _UserRole.bid_specialist
                upgraded += 1
        if upgraded:
            db.commit()
            print(f"Upgraded {upgraded} user(s) to bid_specialist role: {[u.display_name for u in specialists]}")

        # Migrate existing abandoned projects: old free-text reason → abandon_notes, reason → 资质不符
        from .models.project import ProjectInfo as _ProjectInfo, ProjectStatus as _ProjectStatus
        abandoned = db.query(_ProjectInfo).filter(_ProjectInfo.status == _ProjectStatus.abandoned).all()
        migrated = 0
        for p in abandoned:
            old_reason = (p.abandon_reason or "").strip()
            # 已是标准选项则跳过（幂等）
            if old_reason in ("资质不符", "价格太低", "") and (p.abandon_notes or "").strip():
                # reason 已是选项且 notes 已有内容，认为已迁移
                if old_reason in ("资质不符", "价格太低"):
                    continue
            if old_reason and old_reason not in ("资质不符", "价格太低"):
                # 旧自由文本移到 notes，reason 设为默认选项"资质不符"
                p.abandon_notes = old_reason
                p.abandon_reason = "资质不符"
                migrated += 1
            elif not old_reason:
                # reason 为空也归为"资质不符"
                p.abandon_reason = "资质不符"
                migrated += 1
        if migrated:
            db.commit()
            print(f"Migrated {migrated} abandoned project(s): reason → 资质不符, old text → abandon_notes")
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
from .api.documents import router as documents_router
from .api.scrape import router as scrape_router

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(stats_router)
app.include_router(logs_router)
app.include_router(orgs_router)
app.include_router(platforms_router)
app.include_router(managers_router)
app.include_router(projects_router)
app.include_router(documents_router)
app.include_router(scrape_router)
