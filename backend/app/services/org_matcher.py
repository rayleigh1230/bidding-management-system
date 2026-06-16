"""组织/平台匹配创建 helper — 供 documents.py 和 scrape_runner.py 共用。"""
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models.organization import Organization
from ..models.platform import Platform
from ..schemas.dict import OrganizationCreate, PlatformCreate
from ..api.organizations import create_organization as _create_org
from ..api.platforms import create_platform as _create_platform


def match_or_create_org(
    name: str, db: Session, current_user
) -> tuple[int | None, str | None]:
    """按名称匹配组织，无匹配则创建 external 类型。返回 (org_id, matched_name)。"""
    name = (name or "").strip()
    if not name:
        return None, None
    existing = (
        db.query(Organization)
        .filter(
            or_(
                Organization.name == name,
                Organization.name.contains(name),
                Organization.short_name.contains(name),
            )
        )
        .first()
    )
    if existing:
        return existing.id, existing.name
    dup = db.query(Organization).filter(Organization.name == name).first()
    if dup:
        return dup.id, dup.name
    new_org = _create_org(
        OrganizationCreate(name=name, org_type="external"),
        db=db,
        current_user=current_user,
    )
    return new_org.id, new_org.name


def match_or_create_platform(
    name: str, db: Session, current_user
) -> tuple[int | None, str | None]:
    """按名称匹配平台，无匹配则创建。"""
    name = (name or "").strip()
    if not name:
        return None, None
    existing = (
        db.query(Platform)
        .filter(or_(Platform.name == name, Platform.name.contains(name)))
        .first()
    )
    if existing:
        return existing.id, existing.name
    dup = db.query(Platform).filter(Platform.name == name).first()
    if dup:
        return dup.id, dup.name
    new_pf = _create_platform(PlatformCreate(name=name), db=db, current_user=current_user)
    return new_pf.id, new_pf.name
