# -*- coding: utf-8 -*-
"""
测试数据生成脚本 - 生成20条覆盖全场景的项目数据
用法: python backend/scripts/seed_test_data.py
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

token = None
headers = {}
org_ids = {}
platform_ids = []
manager_ids = []


def login():
    global token, headers
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin", "password": "admin123"
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print("[OK] Login")


def _get_or_create(endpoint, name, payload):
    """Get existing record by keyword search, or create new."""
    resp = requests.get(f"{BASE_URL}{endpoint}", params={"keyword": name, "page_size": 1}, headers=headers)
    items = resp.json().get("items", [])
    if items:
        return items[0]["id"]
    resp = requests.post(f"{BASE_URL}{endpoint}", json=payload, headers=headers)
    assert resp.status_code == 200, f"Create failed [{name}]: {resp.text}"
    return resp.json()["id"]


def create_prerequisites():
    orgs = [
        {"name": "浙江省大数据发展管理局", "short_name": "省大数据局", "contact_person": "王建国", "contact_phone": "0571-87012345"},
        {"name": "杭州市教育局", "short_name": "市教育局", "contact_person": "李明华", "contact_phone": "0571-87054321"},
        {"name": "宁波市卫生健康委员会", "short_name": "宁波卫健委", "contact_person": "陈志强", "contact_phone": "0574-87123456"},
        {"name": "浙江中诚招标代理有限公司", "short_name": "中诚招标", "contact_person": "赵晓峰", "contact_phone": "0571-88012345"},
        {"name": "杭州国泰工程咨询有限公司", "short_name": "国泰咨询", "contact_person": "钱丽华", "contact_phone": "0571-88054321"},
        {"name": "浙江华信科技有限公司", "short_name": "华信科技", "contact_person": "孙伟", "contact_phone": "0571-89012345"},
        {"name": "杭州远望信息技术股份有限公司", "short_name": "远望信息", "contact_person": "周敏", "contact_phone": "0571-89054321"},
        {"name": "宁波海天软件有限公司", "short_name": "海天软件", "contact_person": "吴刚", "contact_phone": "0574-89123456"},
    ]
    for o in orgs:
        org_ids[o["name"]] = _get_or_create("/api/organizations", o["name"], o)
    print(f"[OK] {len(orgs)} orgs ready")

    plats = [
        {"name": "浙江政府采购网", "url": "https://ccgp-zhejiang.gov.cn"},
        {"name": "杭州市公共资源交易平台", "url": "https://hzggzy.gov.cn"},
        {"name": "浙江中介超市", "url": "https://zjzjcs.gov.cn"},
    ]
    for p in plats:
        platform_ids.append(_get_or_create("/api/platforms", p["name"], p))
    print(f"[OK] {len(plats)} platforms ready")

    mgrs = [
        {"name": "张三", "phone": "13800001111", "company": "浙江华信科技有限公司"},
        {"name": "李四", "phone": "13800002222", "company": "浙江华信科技有限公司"},
        {"name": "王五", "phone": "13800003333", "company": "浙江华信科技有限公司"},
        {"name": "赵六", "phone": "13800004444", "company": "杭州远望信息技术股份有限公司"},
        {"name": "钱七", "phone": "13800005555", "company": "宁波海天软件有限公司"},
    ]
    for m in mgrs:
        manager_ids.append(_get_or_create("/api/managers", m["name"], m))
    print(f"[OK] {len(mgrs)} managers ready")


def api(method, path, data=None):
    resp = getattr(requests, method)(f"{BASE_URL}{path}", json=data, headers=headers)
    assert resp.status_code == 200, f"API {method} {path} failed: {resp.text}"
    return resp.json()


def create_proj(data):
    return api("post", "/api/projects", data)["id"]

def update_proj(pid, data):
    return api("put", f"/api/projects/{pid}", data)

def publish(pid):
    api("post", f"/api/projects/{pid}/publish")

def prepare(pid):
    api("post", f"/api/projects/{pid}/prepare")

def submit(pid):
    api("post", f"/api/projects/{pid}/submit")

def abandon(pid, reason=""):
    api("post", f"/api/projects/{pid}/abandon", {"reason": reason})


def seed():
    n = [0]
    def ok(label):
        n[0] += 1
        print(f"[OK] {n[0]}/20 {label}")

    # Helper refs
    O = org_ids  # O["name"] -> id
    P = platform_ids  # P[0], P[1], P[2]
    M = manager_ids  # M[0]..M[4]

    # ========== WON (6) ==========

    # 1 - WON, amount type, deposit returned, contract signed+returned
    pid = create_proj({"bidding_type": "公开招标", "project_name": "智慧城市数据平台建设项目",
        "bidding_unit_id": O["浙江省大数据发展管理局"], "region": '["浙江省","杭州市","西湖区"]',
        "manager_ids": [M[0], M[1]], "description": "建设城市级大数据平台，实现数据采集、治理、共享、开放全流程管理"})
    update_proj(pid, {"agency_id": O["浙江中诚招标代理有限公司"], "publish_platform_id": P[0],
        "tags": ["大数据", "智慧城市", "数据平台"], "registration_deadline": "2026-02-15",
        "bid_deadline": "2026-03-01", "budget_amount": 5800000, "control_price_type": "金额",
        "control_price_upper": 5800000, "control_price_lower": 4640000, "bidding_notes": "项目规模较大"})
    publish(pid)
    update_proj(pid, {"bid_method": "独立", "bid_status": "已报名", "has_deposit": True,
        "deposit_status": "已缴纳", "deposit_amount": 100000, "deposit_date": "2026-02-14",
        "our_price": 5280000, "bid_notes": "技术方案突出数据治理能力"})
    prepare(pid)
    submit(pid)
    update_proj(pid, {"competitors": [{"org_id": O["杭州远望信息技术股份有限公司"], "price": 5520000},
        {"org_id": O["宁波海天软件有限公司"], "price": 5400000}],
        "scoring_details": [{"name": "技术方案", "score": 42}, {"name": "商务报价", "score": 28},
            {"name": "企业资信", "score": 18}, {"name": "服务方案", "score": 10}],
        "is_won": True, "winning_org_id": O["浙江华信科技有限公司"],
        "result_deposit_status": "已收回", "deposit_return_date": "2026-03-20",
        "contract_number": "ZJDATA-2026-001", "contract_status": "已签订已收回",
        "contract_amount": 5280000, "result_notes": "技术方案评分最高"})
    ok("智慧城市数据平台 - WON")

    # 2 - WON, discount rate, consortium, deposit returned
    pid = create_proj({"bidding_type": "公开招标", "project_name": "政务云服务采购项目",
        "bidding_unit_id": O["浙江省大数据发展管理局"], "region": '["浙江省","杭州市","上城区"]',
        "manager_ids": [M[0]], "description": "为省级政务系统提供云计算基础设施服务"})
    update_proj(pid, {"agency_id": O["杭州国泰工程咨询有限公司"], "publish_platform_id": P[0],
        "tags": ["云计算", "政务云"], "registration_deadline": "2026-01-20",
        "bid_deadline": "2026-02-10", "budget_amount": 12000000, "control_price_type": "折扣率",
        "control_price_upper": 100, "control_price_lower": 70})
    publish(pid)
    update_proj(pid, {"partner_ids": [O["杭州远望信息技术股份有限公司"]], "bid_method": "联合体",
        "bid_status": "已报名", "has_deposit": True, "deposit_status": "已缴纳",
        "deposit_amount": 200000, "deposit_date": "2026-01-19", "our_price": 88})
    prepare(pid)
    submit(pid)
    update_proj(pid, {"competitors": [{"org_id": O["宁波海天软件有限公司"], "price": 92}],
        "scoring_details": [{"name": "技术方案", "score": 38}, {"name": "商务报价", "score": 30},
            {"name": "企业资信", "score": 20}, {"name": "服务方案", "score": 9}],
        "is_won": True, "winning_org_id": O["浙江华信科技有限公司"],
        "result_deposit_status": "已收回", "deposit_return_date": "2026-03-05",
        "contract_number": "ZJGOV-CLOUD-2026-001", "contract_status": "已签订已收回",
        "contract_amount": 10560000, "result_notes": "联合体方案获高度认可"})
    ok("政务云服务采购 - WON")

    # 3 - WON, float-down rate, contract signed not returned
    pid = create_proj({"bidding_type": "公开招标", "project_name": "网络安全等保测评服务项目",
        "bidding_unit_id": O["浙江省大数据发展管理局"], "region": '["浙江省","杭州市","拱墅区"]',
        "manager_ids": [M[2]]})
    update_proj(pid, {"agency_id": O["浙江中诚招标代理有限公司"], "publish_platform_id": P[0],
        "tags": ["网络安全", "等保测评"], "registration_deadline": "2026-03-01",
        "bid_deadline": "2026-03-15", "budget_amount": 2000000, "control_price_type": "下浮率",
        "control_price_upper": 10, "control_price_lower": 5})
    publish(pid)
    update_proj(pid, {"bid_method": "独立", "bid_status": "已报名", "has_deposit": True,
        "deposit_status": "已缴纳", "deposit_amount": 50000, "deposit_date": "2026-02-28", "our_price": 8})
    prepare(pid)
    submit(pid)
    update_proj(pid, {"competitors": [{"org_id": O["宁波海天软件有限公司"], "price": 7}],
        "is_won": True, "winning_org_id": O["浙江华信科技有限公司"],
        "result_deposit_status": "未收回", "contract_number": "ZJSEC-2026-015",
        "contract_status": "已签订未收回", "contract_amount": 1840000, "result_notes": "等待合同原件寄回"})
    ok("网络安全等保测评 - WON")

    # 4 - WON, invited, scoring details, contract unsigned
    pid = create_proj({"bidding_type": "邀请招标", "project_name": "教育信息化设备采购项目",
        "bidding_unit_id": O["杭州市教育局"], "region": '["浙江省","杭州市","滨江区"]',
        "manager_ids": [M[1]], "description": "为全市中小学采购智慧教室设备"})
    update_proj(pid, {"agency_id": O["杭州国泰工程咨询有限公司"], "publish_platform_id": P[1],
        "tags": ["教育信息化", "智慧校园"], "registration_deadline": "2026-02-28",
        "bid_deadline": "2026-03-10", "budget_amount": 3500000, "control_price_type": "金额",
        "control_price_upper": 3500000})
    publish(pid)
    update_proj(pid, {"bid_method": "独立", "bid_status": "已报名", "has_deposit": True,
        "deposit_status": "已缴纳", "deposit_amount": 70000, "deposit_date": "2026-02-25",
        "our_price": 3180000})
    prepare(pid)
    submit(pid)
    update_proj(pid, {"competitors": [{"org_id": O["杭州远望信息技术股份有限公司"], "price": 3350000},
        {"org_id": O["宁波海天软件有限公司"], "price": 3280000}],
        "scoring_details": [{"name": "技术方案", "score": 40}, {"name": "商务报价", "score": 29},
            {"name": "企业资信", "score": 19}, {"name": "服务方案", "score": 10}],
        "is_won": True, "winning_org_id": O["浙江华信科技有限公司"],
        "result_deposit_status": "已收回", "deposit_return_date": "2026-04-01",
        "contract_status": "未签订", "result_notes": "等待签订合同"})
    ok("教育信息化设备采购 - WON")

    # 5 - WON, cooperate bid, multiple competitors
    pid = create_proj({"bidding_type": "公开招标", "project_name": "医院HIS系统升级改造项目",
        "bidding_unit_id": O["宁波市卫生健康委员会"], "region": '["浙江省","宁波市","鄞州区"]',
        "manager_ids": [M[0], M[2]]})
    update_proj(pid, {"agency_id": O["浙江中诚招标代理有限公司"], "publish_platform_id": P[0],
        "tags": ["医疗信息化", "HIS系统"], "registration_deadline": "2026-01-31",
        "bid_deadline": "2026-02-20", "budget_amount": 4200000, "control_price_type": "金额",
        "control_price_upper": 4200000})
    publish(pid)
    update_proj(pid, {"partner_ids": [O["杭州远望信息技术股份有限公司"]], "bid_method": "配合",
        "bid_status": "已报名", "has_deposit": True, "deposit_status": "已缴纳",
        "deposit_amount": 80000, "deposit_date": "2026-01-28", "our_price": 3960000})
    prepare(pid)
    submit(pid)
    update_proj(pid, {"competitors": [{"org_id": O["宁波海天软件有限公司"], "price": 4050000}],
        "is_won": True, "winning_org_id": O["浙江华信科技有限公司"],
        "result_deposit_status": "已收回", "deposit_return_date": "2026-03-15",
        "contract_number": "NB-HEALTH-2026-008", "contract_status": "已签订已收回",
        "contract_amount": 3960000, "result_notes": "配合投标模式成功"})
    ok("医院HIS系统升级 - WON")

    # 6 - WON, invited, prequalification, companion bid
    pid = create_proj({"bidding_type": "邀请招标", "project_name": "数字档案馆建设项目",
        "bidding_unit_id": O["浙江省大数据发展管理局"], "region": '["浙江省","杭州市","西湖区"]',
        "manager_ids": [M[1], M[3]]})
    update_proj(pid, {"publish_platform_id": P[1], "tags": ["数字档案", "信息化"],
        "registration_deadline": "2026-03-10", "bid_deadline": "2026-03-25",
        "budget_amount": 2800000, "control_price_type": "金额", "control_price_upper": 2800000,
        "is_prequalification": True})
    publish(pid)
    update_proj(pid, {"partner_ids": [O["宁波海天软件有限公司"]], "bid_method": "陪标",
        "bid_status": "已报名", "has_deposit": False, "deposit_status": "无", "our_price": 2560000})
    prepare(pid)
    submit(pid)
    update_proj(pid, {"is_won": True, "winning_org_id": O["浙江华信科技有限公司"],
        "contract_number": "ZJ-ARCHIVE-2026-003", "contract_status": "已签订已收回",
        "contract_amount": 2560000, "result_notes": "陪标策略执行顺利"})
    ok("数字档案馆建设 - WON")

    # ========== SUBMITTED (2) ==========

    # 7 - SUBMITTED, amount type, waiting for result
    pid = create_proj({"bidding_type": "公开招标", "project_name": "智能交通监控系统采购项目",
        "bidding_unit_id": O["浙江省大数据发展管理局"], "region": '["浙江省","杭州市","余杭区"]',
        "manager_ids": [M[0]], "description": "城市智能交通监控系统建设"})
    update_proj(pid, {"agency_id": O["浙江中诚招标代理有限公司"], "publish_platform_id": P[0],
        "tags": ["智能交通", "视频监控"], "registration_deadline": "2026-03-20",
        "bid_deadline": "2026-04-05", "budget_amount": 6500000, "control_price_type": "金额",
        "control_price_upper": 6500000, "control_price_lower": 5200000})
    publish(pid)
    update_proj(pid, {"bid_method": "独立", "bid_status": "已投标", "has_deposit": True,
        "deposit_status": "已缴纳", "deposit_amount": 130000, "deposit_date": "2026-03-18",
        "our_price": 5980000})
    prepare(pid)
    submit(pid)
    ok("智能交通监控系统 - SUBMITTED")

    # 8 - SUBMITTED, intermediary, discount rate
    pid = create_proj({"bidding_type": "中介超市", "project_name": "社区卫生服务信息化建设项目",
        "bidding_unit_id": O["宁波市卫生健康委员会"], "region": '["浙江省","宁波市","海曙区"]',
        "manager_ids": [M[2]]})
    update_proj(pid, {"publish_platform_id": P[2], "tags": ["社区卫生", "信息化"],
        "registration_deadline": "2026-04-01", "bid_deadline": "2026-04-10",
        "budget_amount": 1500000, "control_price_type": "折扣率",
        "control_price_upper": 100, "control_price_lower": 60})
    publish(pid)
    update_proj(pid, {"bid_method": "独立", "bid_status": "已投标", "has_deposit": True,
        "deposit_status": "已缴纳", "deposit_amount": 30000, "deposit_date": "2026-03-30",
        "our_price": 82})
    prepare(pid)
    submit(pid)
    ok("社区卫生信息化 - SUBMITTED")

    # ========== LOST (3) ==========

    # 9 - LOST, amount, loss analysis
    pid = create_proj({"bidding_type": "公开招标", "project_name": "水利工程智能监测系统项目",
        "bidding_unit_id": O["浙江省大数据发展管理局"], "region": '["浙江省","杭州市","富阳区"]',
        "manager_ids": [M[1]]})
    update_proj(pid, {"agency_id": O["杭州国泰工程咨询有限公司"], "publish_platform_id": P[0],
        "tags": ["水利", "物联网", "监测"], "registration_deadline": "2026-02-10",
        "bid_deadline": "2026-02-28", "budget_amount": 3800000, "control_price_type": "金额",
        "control_price_upper": 3800000})
    publish(pid)
    update_proj(pid, {"bid_method": "独立", "bid_status": "已报名", "has_deposit": True,
        "deposit_status": "已缴纳", "deposit_amount": 76000, "deposit_date": "2026-02-08",
        "our_price": 3580000})
    prepare(pid)
    submit(pid)
    update_proj(pid, {"competitors": [{"org_id": O["杭州远望信息技术股份有限公司"], "price": 3350000},
        {"org_id": O["宁波海天软件有限公司"], "price": 3480000}],
        "is_won": False, "result_deposit_status": "已收回", "deposit_return_date": "2026-03-20",
        "lost_analysis": "竞争对手报价更低，商务分领先较多。下次应更注重报价策略。",
        "result_notes": "商务报价差距较大"})
    ok("水利监测系统 - LOST")

    # 10 - LOST, discount rate, scoring
    pid = create_proj({"bidding_type": "公开招标", "project_name": "生态环境监测平台建设项目",
        "bidding_unit_id": O["浙江省大数据发展管理局"], "region": '["浙江省","杭州市","临安区"]',
        "manager_ids": [M[0], M[2]]})
    update_proj(pid, {"agency_id": O["浙江中诚招标代理有限公司"], "publish_platform_id": P[0],
        "tags": ["生态环境", "监测平台"], "registration_deadline": "2026-01-15",
        "bid_deadline": "2026-02-05", "budget_amount": 4500000, "control_price_type": "折扣率",
        "control_price_upper": 100, "control_price_lower": 60})
    publish(pid)
    update_proj(pid, {"partner_ids": [O["杭州远望信息技术股份有限公司"]], "bid_method": "联合体",
        "bid_status": "已报名", "has_deposit": True, "deposit_status": "已缴纳",
        "deposit_amount": 90000, "deposit_date": "2026-01-12", "our_price": 90})
    prepare(pid)
    submit(pid)
    update_proj(pid, {"competitors": [{"org_id": O["宁波海天软件有限公司"], "price": 85}],
        "scoring_details": [{"name": "技术方案", "score": 35}, {"name": "商务报价", "score": 25},
            {"name": "企业资信", "score": 17}, {"name": "服务方案", "score": 8}],
        "is_won": False, "result_deposit_status": "已收回", "deposit_return_date": "2026-03-10",
        "lost_analysis": "折扣率偏高导致商务分较低，联合体资质加分不如预期。",
        "result_notes": "商务分差距导致落标"})
    ok("生态环境监测平台 - LOST")

    # 11 - LOST, invited, float-down, consortium
    pid = create_proj({"bidding_type": "邀请招标", "project_name": "智慧社区综合服务平台项目",
        "bidding_unit_id": O["杭州市教育局"], "region": '["浙江省","杭州市","萧山区"]',
        "manager_ids": [M[3]]})
    update_proj(pid, {"publish_platform_id": P[1], "tags": ["智慧社区", "综合服务"],
        "registration_deadline": "2026-03-05", "bid_deadline": "2026-03-20",
        "budget_amount": 2200000, "control_price_type": "下浮率",
        "control_price_upper": 8, "control_price_lower": 3})
    publish(pid)
    update_proj(pid, {"partner_ids": [O["宁波海天软件有限公司"]], "bid_method": "联合体",
        "bid_status": "已报名", "has_deposit": True, "deposit_status": "已缴纳",
        "deposit_amount": 44000, "deposit_date": "2026-03-03", "our_price": 6})
    prepare(pid)
    submit(pid)
    update_proj(pid, {"competitors": [{"org_id": O["杭州远望信息技术股份有限公司"], "price": 7}],
        "is_won": False, "result_deposit_status": "已收回", "deposit_return_date": "2026-04-05",
        "lost_analysis": "下浮率报低了，竞争对手下浮更多但价格更优。",
        "result_notes": "价格策略失误"})
    ok("智慧社区综合服务 - LOST")

    # ========== PREPARING (2) ==========

    # 12 - PREPARING, prequalification, registered, deposit
    pid = create_proj({"bidding_type": "入围分项", "project_name": "城市地下管网智能检测项目",
        "bidding_unit_id": O["浙江省大数据发展管理局"], "region": '["浙江省","杭州市","钱塘区"]',
        "manager_ids": [M[1], M[4]]})
    update_proj(pid, {"agency_id": O["浙江中诚招标代理有限公司"], "publish_platform_id": P[0],
        "tags": ["地下管网", "检测", "物联网"], "registration_deadline": "2026-04-15",
        "bid_deadline": "2026-04-30", "budget_amount": 3000000, "control_price_type": "金额",
        "control_price_upper": 3000000})
    publish(pid)
    update_proj(pid, {"bid_method": "独立", "bid_status": "已报名", "has_deposit": True,
        "deposit_status": "已缴纳", "deposit_amount": 60000, "deposit_date": "2026-04-10",
        "our_price": 2750000, "bid_notes": "正在准备技术方案和商务文件"})
    prepare(pid)
    ok("城市地下管网检测 - PREPARING")

    # 13 - PREPARING, not registered
    pid = create_proj({"bidding_type": "公开招标", "project_name": "公共资源交易系统升级项目",
        "bidding_unit_id": O["浙江省大数据发展管理局"], "region": '["浙江省","杭州市","上城区"]',
        "manager_ids": [M[0]], "description": "升级现有公共资源交易平台，增加电子招投标功能"})
    update_proj(pid, {"publish_platform_id": P[1], "tags": ["公共资源", "交易平台"],
        "registration_deadline": "2026-04-20", "bid_deadline": "2026-05-10",
        "budget_amount": 5000000, "control_price_type": "金额",
        "control_price_upper": 5000000, "control_price_lower": 4000000})
    publish(pid)
    update_proj(pid, {"bid_method": "独立", "bid_status": "未报名",
        "has_deposit": False, "deposit_status": "无"})
    prepare(pid)
    ok("公共资源交易系统 - PREPARING")

    # ========== PUBLISHED (2) ==========

    # 14 - PUBLISHED
    pid = create_proj({"bidding_type": "公开招标", "project_name": "应急指挥中心建设项目",
        "bidding_unit_id": O["浙江省大数据发展管理局"], "region": '["浙江省","杭州市","滨江区"]',
        "manager_ids": [M[2]], "description": "建设应急指挥中心大屏及配套系统"})
    update_proj(pid, {"agency_id": O["杭州国泰工程咨询有限公司"], "publish_platform_id": P[0],
        "tags": ["应急指挥", "大屏"], "registration_deadline": "2026-04-25",
        "bid_deadline": "2026-05-15", "budget_amount": 8000000, "control_price_type": "金额",
        "control_price_upper": 8000000, "control_price_lower": 6400000,
        "bidding_notes": "项目预算充足，需要大屏展示和GIS能力"})
    publish(pid)
    ok("应急指挥中心建设 - PUBLISHED")

    # 15 - PUBLISHED, invited, tags, agency
    pid = create_proj({"bidding_type": "邀请招标", "project_name": "残疾人康复中心信息化设备采购",
        "bidding_unit_id": O["杭州市教育局"], "region": '["浙江省","杭州市","拱墅区"]',
        "manager_ids": [M[3], M[4]]})
    update_proj(pid, {"agency_id": O["浙江中诚招标代理有限公司"], "publish_platform_id": P[1],
        "tags": ["康复设备", "信息化", "无障碍"], "registration_deadline": "2026-04-18",
        "bid_deadline": "2026-05-08", "budget_amount": 1800000, "control_price_type": "金额",
        "control_price_upper": 1800000})
    publish(pid)
    ok("残疾人康复中心设备 - PUBLISHED")

    # ========== FOLLOWING (2) ==========

    # 16 - FOLLOWING, intermediary, basic info only
    create_proj({"bidding_type": "中介超市", "project_name": "文化馆数字化改造项目",
        "bidding_unit_id": O["浙江省大数据发展管理局"], "region": '["浙江省","宁波市","镇海区"]',
        "manager_ids": [M[4]]})
    ok("文化馆数字化改造 - FOLLOWING")

    # 17 - FOLLOWING, with description and managers
    create_proj({"bidding_type": "公开招标", "project_name": "乡村振兴大数据平台建设项目",
        "bidding_unit_id": O["浙江省大数据发展管理局"], "region": '["浙江省","杭州市","桐庐县"]',
        "manager_ids": [M[0], M[1], M[2]],
        "description": "建设覆盖全县的乡村振兴大数据平台，实现农业数据采集分析、乡村治理数字化、农产品溯源等功能"})
    ok("乡村振兴大数据平台 - FOLLOWING")

    # ========== ABANDONED (3) ==========

    # 18 - ABANDONED from following
    pid = create_proj({"bidding_type": "公开招标", "project_name": "农产品质量追溯系统建设项目",
        "bidding_unit_id": O["浙江省大数据发展管理局"], "region": '["浙江省","杭州市","建德市"]',
        "manager_ids": [M[1]], "description": "建设农产品质量追溯系统"})
    abandon(pid, "项目预算过低，投入产出比不合理，经内部评估后决定放弃")
    ok("农产品质量追溯系统 - ABANDONED")

    # 19 - ABANDONED from published
    pid = create_proj({"bidding_type": "邀请招标", "project_name": "养老服务信息平台建设项目",
        "bidding_unit_id": O["杭州市教育局"], "region": '["浙江省","杭州市","西湖区"]',
        "manager_ids": [M[3]]})
    update_proj(pid, {"publish_platform_id": P[1], "tags": ["养老服务", "信息平台"],
        "registration_deadline": "2026-03-15", "bid_deadline": "2026-04-01",
        "budget_amount": 1200000, "control_price_type": "金额", "control_price_upper": 1200000})
    publish(pid)
    abandon(pid, "资质要求中发现需要特定行业认证，公司暂不具备该资质")
    ok("养老服务信息平台 - ABANDONED")

    # 20 - ABANDONED from preparing
    pid = create_proj({"bidding_type": "公开招标", "project_name": "产业园区智慧安防工程",
        "bidding_unit_id": O["浙江省大数据发展管理局"], "region": '["浙江省","杭州市","余杭区"]',
        "manager_ids": [M[0], M[4]]})
    update_proj(pid, {"agency_id": O["杭州国泰工程咨询有限公司"], "publish_platform_id": P[0],
        "tags": ["智慧安防", "产业园区"], "registration_deadline": "2026-03-25",
        "bid_deadline": "2026-04-10", "budget_amount": 7500000, "control_price_type": "金额",
        "control_price_upper": 7500000})
    publish(pid)
    update_proj(pid, {"partner_ids": [O["杭州远望信息技术股份有限公司"]], "bid_method": "联合体",
        "bid_status": "已报名", "has_deposit": True, "deposit_status": "未缴纳",
        "deposit_amount": 150000})
    prepare(pid)
    abandon(pid, "联合体伙伴临时退出，无法独立完成该项目，且保证金缴纳时间紧迫")
    ok("园区智慧安防工程 - ABANDONED")


def clean_all_projects():
    """Delete all existing projects."""
    resp = requests.get(f"{BASE_URL}/api/projects?page_size=100", headers=headers)
    data = resp.json()
    for item in data["items"]:
        requests.delete(f"{BASE_URL}/api/projects/{item['id']}", headers=headers)
    print(f"[OK] Cleaned {data['total']} existing projects")


def main():
    print("=" * 50)
    print("Seeding test data...")
    print("=" * 50)
    login()
    create_prerequisites()
    clean_all_projects()
    seed()

    # Verify
    resp = requests.get(f"{BASE_URL}/api/projects?page_size=100", headers=headers)
    data = resp.json()
    print("\n" + "=" * 50)
    print(f"Done! Total: {data['total']} projects")

    status_cn = {"following": "跟进中", "published": "已发公告", "preparing": "准备投标",
                 "submitted": "已投标", "won": "已中标", "lost": "未中标", "abandoned": "已放弃"}
    counts = {}
    for item in data["items"]:
        s = item["status"]
        counts[s] = counts.get(s, 0) + 1
    print("\nStatus distribution:")
    for s in ["won", "submitted", "lost", "preparing", "published", "following", "abandoned"]:
        if s in counts:
            print(f"  {status_cn[s]}: {counts[s]}")
    print("=" * 50)


if __name__ == "__main__":
    main()
