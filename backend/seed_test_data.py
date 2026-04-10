"""
生成 20 条测试项目数据，覆盖全场景。

场景覆盖：
 1.  跟进中 - 公开招标（刚创建，最简信息）
 2.  跟进中 - 邀请招标（完整基本信息）
 3.  已发公告 - 公开招标，金额控制价
 4.  已发公告 - 中介超市，无报名截止
 5.  未报名 - 公开招标，有报名截止未勾选
 6.  已报名 - 邀请招标，折扣率控制价
 7.  准备投标 - 独立投标，保证金已缴纳，金额控制价
 8.  准备投标 - 联合体，下浮率，合作单位
 9.  准备投标 - 配合投标
10.  已投标 - 独立投标，保证金未收回，等待结果
11.  已投标 - 联合体，我方牵头，有参标单位
12.  已中标 - 独立投标，金额控制价，合同已签订已收回
13.  已中标 - 联合体投标，折扣率，合同未签订
14.  已中标 - 入围标 (is_prequalification)，多家中标
15.  未中标 - 独立投标，有未中标分析
16.  未中标 - 陪标投标
17.  已流标 - 独立投标
18.  已放弃 - 从跟进中放弃
19.  已放弃 - 从已发公告放弃
20.  入围分项 - 关联入围标(#14)，准备投标

用法: cd backend && python seed_test_data.py
"""

import sqlite3
import json
from datetime import datetime, date

DB_PATH = "data/app.db"

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")
cur = conn.cursor()

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ============================================================
# 第一步：字典数据
# ============================================================

# --- 招标单位 / 竞争对手 / 合作单位 ---
ext_orgs = [
    # 招标单位（甲方）
    ("杭州市教育局", "市教育局", "王建国", "0571-87012345"),
    ("宁波市交通运输局", "市交通局", "李志强", "0574-87123456"),
    ("温州市卫生健康委员会", "市卫健委", "陈明华", "0577-88234567"),
    ("嘉兴市住房和城乡建设局", "市住建局", "赵伟", "0573-89345678"),
    ("金华市自然资源和规划局", "市资规局", "孙丽", "0579-80456789"),
    ("台州市公安局", "市公安局", "周涛", "0576-81567890"),
    ("绍兴市水利局", "市水利局", "吴刚", "0575-88678901"),
    ("湖州市文广旅体局", "市文广旅体局", "郑芳", "0572-89789012"),
    ("衢州市生态环境局", "市生态环境局", "钱进", "0570-80890123"),
    ("丽水市农业农村局", "市农业局", "冯磊", "0578-81901234"),
    # 竞争对手 / 合作单位
    ("杭州华信科技有限公司", "华信科技", "林建", "0571-88001111"),
    ("宁波智联信息技术有限公司", "智联信息", "张华", "0574-88002222"),
    ("温州正达建设工程检测有限公司", "正达检测", "刘明", "0577-88003333"),
    ("浙江大地测绘有限公司", "大地测绘", "陈波", "0571-88004444"),
    ("杭州云图数据科技有限公司", "云图数据", "杨洋", "0571-88005555"),
    # 代理单位
    ("浙江天诚招标代理有限公司", "天诚代理", "吴丽", "0571-88006666"),
    ("杭州公信工程咨询有限公司", "公信咨询", "何军", "0571-88007777"),
]

for name, short, person, phone in ext_orgs:
    cur.execute(
        "INSERT INTO organizations (name, short_name, contact_person, contact_phone, org_type, notes, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        (name, short, person, phone, "external", "", now, now),
    )

# ID 映射：1=浙江意诚(ours), 2=教育局, 3=交通局, 4=卫健委, 5=住建局, 6=资规局,
#          7=公安局, 8=水利局, 9=文广旅体局, 10=生态环境局, 11=农业局,
#          12=华信科技, 13=智联信息, 14=正达检测, 15=大地测绘, 16=云图数据,
#          17=天诚代理, 18=公信咨询
OUR_ID = 1

# --- 平台 ---
platforms = [
    ("浙江省政府采购网", "https://ccgp-zhejiang.gov.cn"),
    ("中介超市网上服务平台", "https://zjcs.zj.gov.cn"),
    ("中国招标投标公共服务平台", "https://www.cebpubservice.com"),
]
for name, url in platforms:
    cur.execute("INSERT INTO platforms (name, url, created_at) VALUES (?,?,?)", (name, url, now))
# platform IDs: 1=政府采购网, 2=中介超市, 3=中国招投标

# --- 负责人 ---
managers = [
    ("李明", "13800001111", "杭州总部", "高级项目经理"),
    ("王芳", "13800002222", "杭州总部", "项目主管"),
    ("陈军", "13800003333", "宁波分部", "客户经理"),
    ("赵丽", "13800004444", "温州分部", "业务专员"),
]
for name, phone, company, notes in managers:
    cur.execute("INSERT INTO managers (name, phone, company, notes, created_at) VALUES (?,?,?,?,?)",
                (name, phone, company, notes, now))
# manager IDs: 1=李明, 2=王芳, 3=陈军, 4=赵丽

# --- 投标专员 ---
cur.execute(
    "INSERT INTO users (username, password_hash, display_name, role, phone, is_active, created_at) VALUES (?,?,?,?,?,?,?)",
    ("zhangwei", "$2b$12$5RAgQ/3W51RiXKD2S46XueiVCywo.8xfjRus.SkER1AG9ukFXobUy",
     "张伟", "user", "13800005555", 1, now),
)
# specialist user ID: 2 (admin is 1)

print("字典数据完成")

# ============================================================
# 第二步：项目数据
# ============================================================

def ins(sql, params):
    cur.execute(sql, params)
    return cur.lastrowid


def make_project(**kw):
    """插入 project_infos 记录，返回 id"""
    defaults = dict(
        bidding_type="public", project_name="", bidding_unit_id=None,
        region="", manager_ids="[]", status="following", description="",
        abandon_reason="", parent_project_id=None, created_by=1,
        created_at=now, updated_at=now,
        # 招标信息
        agency_id=None, publish_platform_id=None, tags="[]",
        registration_deadline=None, bid_deadline=None, budget_amount=0,
        control_price_type="amount", control_price_upper=None, control_price_lower=None,
        is_prequalification=0, bid_specialist_id=None, bid_documents="[]", bidding_notes="",
        # 投标信息
        partner_ids="[]", bid_method="independent", bid_status="registered", is_consortium_lead=1,
        has_deposit=0, deposit_status="none", deposit_amount=0,
        deposit_date=None, deposit_return_date=None, bid_files="[]", our_price=0, bid_notes="",
        # 投标结果
        competitors="[]", scoring_details="[]", result_deposit_status=None,
        is_won=0, is_bid_failed=0, winning_org_id=None, winning_org_ids="[]",
        winning_price=None, winning_amount=None, lost_analysis="",
        contract_number="", contract_status="none", contract_amount=0, result_notes="",
    )
    defaults.update(kw)
    cols = list(defaults.keys())
    vals = [defaults[c] for c in cols]
    placeholders = ",".join(["?"] * len(cols))
    col_str = ",".join(cols)
    return ins(f"INSERT INTO project_infos ({col_str}) VALUES ({placeholders})", vals)


# ---- 1. 跟进中 - 公开招标（刚创建） ----
make_project(
    project_name="杭州市智慧校园信息化建设项目",
    bidding_type="public", status="following",
    bidding_unit_id=2,  # 教育局
    region=json.dumps(["浙江省", "杭州市", "西湖区"]),
    manager_ids=json.dumps([1]),
    description="建设覆盖全市中小学的智慧校园管理平台，包含教务管理、在线考试、数据分析等模块。",
)

# ---- 2. 跟进中 - 邀请招标（完整基本信息） ----
make_project(
    project_name="宁波市公路桥梁安全监测系统采购项目",
    bidding_type="invited", status="following",
    bidding_unit_id=3,  # 交通局
    region=json.dumps(["浙江省", "宁波市", "鄞州区"]),
    manager_ids=json.dumps([1, 3]),
    description="为宁波市主要公路桥梁安装智能监测设备，实现结构健康实时监测和预警。",
)

# ---- 3. 已发公告 - 公开招标，金额控制价 ----
make_project(
    project_name="温州市医院智慧后勤管理系统项目",
    bidding_type="public", status="published",
    bidding_unit_id=4,  # 卫健委
    region=json.dumps(["浙江省", "温州市", "鹿城区"]),
    manager_ids=json.dumps([2]),
    description="建设覆盖温州市级医院的智慧后勤管理平台，含设备管理、能源监控、安防联动等子系统。",
    agency_id=17, publish_platform_id=1,
    tags=json.dumps(["信息化", "医疗", "物联网"]),
    registration_deadline="2026-04-15", bid_deadline="2026-04-25",
    budget_amount=6500000, control_price_type="amount",
    control_price_upper=6000000, control_price_lower=5000000,
    bid_specialist_id=2, bidding_notes="需提供本地化运维服务，质保期不少于3年。",
)

# ---- 4. 已发公告 - 中介超市，无报名截止 → 纯已发公告 ----
make_project(
    project_name="嘉兴市数字档案管理系统升级项目",
    bidding_type="intermediary", status="published",
    bidding_unit_id=5,  # 住建局
    region=json.dumps(["浙江省", "嘉兴市", "南湖区"]),
    manager_ids=json.dumps([4]),
    description="对现有数字档案系统进行升级改造，增加电子签章、OCR识别、智能分类等功能。",
    publish_platform_id=2,
    tags=json.dumps(["信息化", "档案管理"]),
    budget_amount=1200000, control_price_type="discount_rate",
    control_price_upper=95.0, control_price_lower=80.0,
)

# ---- 5. 未报名 - 公开招标，有报名截止未勾选 ----
make_project(
    project_name="衢州市环境监测站实验室信息管理系统项目",
    bidding_type="public", status="not_registered",
    bidding_unit_id=10,  # 生态环境局
    region=json.dumps(["浙江省", "衢州市", "柯城区"]),
    manager_ids=json.dumps([3]),
    description="建设实验室信息管理系统(LIMS)，实现样品管理、检测流程、报告生成等全流程数字化。",
    agency_id=17, publish_platform_id=1,
    registration_deadline="2026-04-18", bid_deadline="2026-04-28",
    budget_amount=2800000, control_price_type="amount",
    control_price_upper=2600000, control_price_lower=2200000,
    bid_specialist_id=2,
)

# ---- 6. 已报名 - 邀请招标，折扣率控制价 ----
make_project(
    project_name="丽水市农产品质量安全追溯平台项目",
    bidding_type="invited", status="registered",
    bidding_unit_id=11,  # 农业局
    region=json.dumps(["浙江省", "丽水市", "莲都区"]),
    manager_ids=json.dumps([4, 1]),
    description="建设农产品质量安全追溯平台，实现从田间到餐桌的全链条追溯管理。",
    agency_id=18, publish_platform_id=1,
    tags=json.dumps(["农业", "追溯", "信息化"]),
    registration_deadline="2026-04-12", bid_deadline="2026-04-22",
    budget_amount=3500000, control_price_type="discount_rate",
    control_price_upper=92.0, control_price_lower=78.0,
    bid_specialist_id=2,
)

# ---- 7. 准备投标 - 独立投标，保证金已缴纳，金额控制价 ----
make_project(
    project_name="金华市国土空间规划一张图系统项目",
    bidding_type="public", status="preparing",
    bidding_unit_id=6,  # 资规局
    region=json.dumps(["浙江省", "金华市", "婺城区"]),
    manager_ids=json.dumps([1, 2]),
    description="建设国土空间规划一张图实施监督信息系统，实现规划编制、审批、实施、监督全流程管理。",
    agency_id=17, publish_platform_id=1,
    tags=json.dumps(["GIS", "自然资源", "信息化"]),
    registration_deadline="2026-04-10", bid_deadline="2026-04-20",
    budget_amount=9800000, control_price_type="amount",
    control_price_upper=9500000, control_price_lower=8000000,
    bid_specialist_id=2,
    bid_method="independent", has_deposit=1, deposit_status="paid",
    deposit_amount=100000, deposit_date="2026-04-12",
    our_price=8800000, bid_notes="已完成投标文件编制，保证金已缴纳。",
)

# ---- 8. 准备投标 - 联合体，下浮率，合作单位 ----
make_project(
    project_name="台州市智慧交通信号控制系统项目",
    bidding_type="public", status="preparing",
    bidding_unit_id=7,  # 公安局
    region=json.dumps(["浙江省", "台州市", "椒江区"]),
    manager_ids=json.dumps([3]),
    description="建设城区智慧交通信号控制系统，实现自适应信号控制、交通流量分析、拥堵预警等功能。",
    agency_id=17, publish_platform_id=1,
    tags=json.dumps(["智慧交通", "AI", "物联网"]),
    registration_deadline="2026-03-25", bid_deadline="2026-04-15",
    budget_amount=15000000, control_price_type="float_down_rate",
    control_price_upper=15.0, control_price_lower=5.0,
    bid_specialist_id=2,
    bid_method="consortium", is_consortium_lead=1,
    partner_ids=json.dumps([12]),  # 华信科技
    has_deposit=1, deposit_status="paid",
    deposit_amount=200000, deposit_date="2026-03-28",
    our_price=10.5, bid_notes="联合体投标，我方为牵头方，华信科技负责硬件部分。",
)

# ---- 9. 准备投标 - 配合投标 ----
make_project(
    project_name="绍兴市城市地下管线综合管理信息系统项目",
    bidding_type="public", status="preparing",
    bidding_unit_id=8,  # 水利局
    region=json.dumps(["浙江省", "绍兴市", "越城区"]),
    manager_ids=json.dumps([2, 4]),
    description="建设城市地下管线综合管理信息系统，实现管线数据采集、动态更新、共享应用。",
    agency_id=18, publish_platform_id=1,
    tags=json.dumps(["地下管线", "GIS", "城市管理"]),
    registration_deadline="2026-04-08", bid_deadline="2026-04-18",
    budget_amount=5600000, control_price_type="amount",
    control_price_upper=5300000, control_price_lower=4500000,
    bid_method="cooperate", partner_ids=json.dumps([15]),  # 大地测绘（配合方）
    has_deposit=0, deposit_status="none",
    our_price=1200000, bid_notes="配合大地测绘投标，我方负责信息化系统开发部分。",
)

# ---- 10. 已投标 - 独立投标，保证金未收回，等待结果 ----
make_project(
    project_name="温州市不动产登记电子证照系统项目",
    bidding_type="public", status="submitted",
    bidding_unit_id=4,  # 卫健委（借用）
    region=json.dumps(["浙江省", "温州市", "瓯海区"]),
    manager_ids=json.dumps([2, 3]),
    description="建设不动产登记电子证照系统，实现电子证照签发、共享、验证等功能。",
    agency_id=17, publish_platform_id=1,
    registration_deadline="2026-03-20", bid_deadline="2026-04-05",
    budget_amount=4200000, control_price_type="amount",
    control_price_upper=4000000, control_price_lower=3500000,
    bid_method="independent",
    has_deposit=1, deposit_status="paid",
    deposit_amount=80000, deposit_date="2026-03-22",
    our_price=3850000,
    result_deposit_status="not_returned",
    competitors=json.dumps([
        {"org_ids": [1], "price": 3850000, "score": 0, "is_shortlisted": False, "is_winning": False},
        {"org_ids": [13], "price": 3650000, "score": 0, "is_shortlisted": False, "is_winning": False},
    ]),
)

# ---- 11. 已投标 - 联合体，我方牵头，有参标单位 ----
make_project(
    project_name="宁波市智慧城管综合指挥平台项目",
    bidding_type="invited", status="submitted",
    bidding_unit_id=3,  # 交通局（借用）
    region=json.dumps(["浙江省", "宁波市", "海曙区"]),
    manager_ids=json.dumps([1]),
    description="建设智慧城管综合指挥平台，集成视频监控、应急指挥、城市管理等功能。",
    agency_id=18, publish_platform_id=1,
    tags=json.dumps(["智慧城市", "指挥平台"]),
    registration_deadline="2026-03-15", bid_deadline="2026-04-01",
    budget_amount=12000000, control_price_type="discount_rate",
    control_price_upper=95.0, control_price_lower=82.0,
    bid_method="consortium", is_consortium_lead=1,
    partner_ids=json.dumps([16]),  # 云图数据
    has_deposit=1, deposit_status="paid",
    deposit_amount=150000, deposit_date="2026-03-18",
    our_price=88.5,
    result_deposit_status="not_returned",
    competitors=json.dumps([
        {"org_ids": [1, 16], "price": 88.5, "score": 0, "is_shortlisted": False, "is_winning": False},
        {"org_ids": [12], "price": 85.0, "score": 0, "is_shortlisted": False, "is_winning": False},
        {"org_ids": [14], "price": 90.0, "score": 0, "is_shortlisted": False, "is_winning": False},
    ]),
)

# ---- 12. 已中标 - 独立投标，金额，合同已签订已收回 ----
make_project(
    project_name="湖州市文旅数字化管理平台建设项目",
    bidding_type="public", status="won",
    bidding_unit_id=9,  # 文广旅体局
    region=json.dumps(["浙江省", "湖州市", "吴兴区"]),
    manager_ids=json.dumps([1]),
    description="建设文化旅游数字化管理平台，包含景区智慧管理、文旅大数据分析、游客服务平台等。",
    agency_id=17, publish_platform_id=1,
    tags=json.dumps(["文旅", "大数据", "信息化"]),
    registration_deadline="2026-03-01", bid_deadline="2026-03-15",
    budget_amount=5800000, control_price_type="amount",
    control_price_upper=5500000, control_price_lower=4500000,
    bid_specialist_id=2,
    bid_method="independent",
    has_deposit=1, deposit_status="paid",
    deposit_amount=50000, deposit_date="2026-03-05",
    our_price=4980000,
    result_deposit_status="returned", deposit_return_date="2026-03-25",
    is_won=1,
    competitors=json.dumps([
        {"org_ids": [1], "price": 4980000, "score": 92.5, "is_shortlisted": False, "is_winning": True},
        {"org_ids": [12], "price": 5200000, "score": 85.0, "is_shortlisted": False, "is_winning": False},
        {"org_ids": [14], "price": 5100000, "score": 83.0, "is_shortlisted": False, "is_winning": False},
    ]),
    winning_org_ids=json.dumps([1]),
    winning_org_id=1, winning_amount=4980000,
    contract_number="HZWL-2026-0042", contract_status="signed_returned",
    contract_amount=4980000,
    result_notes="合同已签订且款项已收回，项目进入实施阶段。",
)

# ---- 13. 已中标 - 联合体投标，折扣率，合同未签订 ----
make_project(
    project_name="金华市智慧消防物联网监控平台项目",
    bidding_type="public", status="won",
    bidding_unit_id=6,  # 资规局（借用）
    region=json.dumps(["浙江省", "金华市", "金东区"]),
    manager_ids=json.dumps([2, 4]),
    description="建设智慧消防物联网监控平台，实现消防设施远程监控、火灾预警、应急指挥联动。",
    agency_id=18, publish_platform_id=1,
    tags=json.dumps(["消防", "物联网", "智慧城市"]),
    registration_deadline="2026-02-25", bid_deadline="2026-03-10",
    budget_amount=8200000, control_price_type="discount_rate",
    control_price_upper=93.0, control_price_lower=80.0,
    bid_method="consortium", is_consortium_lead=1,
    partner_ids=json.dumps([13]),  # 智联信息
    has_deposit=1, deposit_status="paid",
    deposit_amount=120000, deposit_date="2026-02-28",
    our_price=85.5,
    result_deposit_status="returned", deposit_return_date="2026-04-05",
    is_won=1,
    competitors=json.dumps([
        {"org_ids": [1, 13], "price": 85.5, "score": 90.0, "is_shortlisted": False, "is_winning": True},
        {"org_ids": [15], "price": 88.0, "score": 82.0, "is_shortlisted": False, "is_winning": False},
    ]),
    winning_org_ids=json.dumps([1, 13]),
    winning_org_id=1, winning_price=85.5,
    winning_amount=round(85.5 / 93.0 * 8200000, 2),  # 折扣率公式
    contract_number="", contract_status="unsigned",
    contract_amount=0,
    result_notes="联合体中标，合同待签订。",
)

# ---- 14. 已中标 - 入围标 (is_prequalification=true)，多家中标 ----
make_project(
    project_name="浙江省水利工程质量检测机构入围项目",
    bidding_type="public", status="won",
    bidding_unit_id=8,  # 水利局
    region=json.dumps(["浙江省", "杭州市", "上城区"]),
    manager_ids=json.dumps([1, 2, 3]),
    description="浙江省水利工程质量检测机构入围招标，选定多家检测机构进入水利工程质量检测供应商库。",
    agency_id=17, publish_platform_id=1,
    tags=json.dumps(["水利", "检测", "入围"]),
    registration_deadline="2026-02-10", bid_deadline="2026-02-28",
    budget_amount=0, control_price_type="amount",
    is_prequalification=1, bid_specialist_id=2,
    bidding_notes="入围标项目，不设预算金额，入选单位进入供应商库。",
    bid_method="independent",
    has_deposit=1, deposit_status="paid",
    deposit_amount=30000, deposit_date="2026-02-15",
    our_price=0,
    result_deposit_status="returned", deposit_return_date="2026-03-20",
    is_won=1,
    competitors=json.dumps([
        {"org_ids": [1], "price": 0, "score": 95.0, "is_shortlisted": True, "is_winning": True},
        {"org_ids": [14], "price": 0, "score": 88.0, "is_shortlisted": True, "is_winning": True},
        {"org_ids": [15], "price": 0, "score": 82.0, "is_shortlisted": True, "is_winning": True},
        {"org_ids": [12], "price": 0, "score": 78.0, "is_shortlisted": False, "is_winning": False},
    ]),
    winning_org_ids=json.dumps([1, 14, 15]),
    winning_org_id=1,
    winning_price=0, winning_amount=0,
    result_notes="入围标项目，3家单位入围。可关联入围分项项目。",
)
# 记录入围标项目 ID
cur.execute("SELECT last_insert_rowid()")
PARENT_PROJECT_ID = cur.fetchone()[0]

# ---- 15. 未中标 - 独立投标，有分析 ----
make_project(
    project_name="杭州市政务服务中心排队叫号系统升级项目",
    bidding_type="intermediary", status="lost",
    bidding_unit_id=2,  # 教育局（借用）
    region=json.dumps(["浙江省", "杭州市", "拱墅区"]),
    manager_ids=json.dumps([4]),
    description="升级政务服务中心排队叫号系统，增加智能预约、人脸识别取号、窗口智能分配等功能。",
    publish_platform_id=2,
    tags=json.dumps(["政务服务", "智能化"]),
    registration_deadline="2026-02-20", bid_deadline="2026-03-05",
    budget_amount=800000, control_price_type="discount_rate",
    control_price_upper=90.0, control_price_lower=75.0,
    bid_method="independent",
    has_deposit=0, deposit_status="none",
    our_price=82.0,
    is_won=0,
    competitors=json.dumps([
        {"org_ids": [1], "price": 82.0, "score": 80.0, "is_shortlisted": False, "is_winning": False},
        {"org_ids": [16], "price": 78.0, "score": 83.0, "is_shortlisted": False, "is_winning": True},
    ]),
    winning_org_ids=json.dumps([16]),
    winning_org_id=16, winning_price=78.0,
    winning_amount=round(78.0 / 90.0 * 800000, 2),
    lost_analysis="我方折扣率82%高于云图数据的78%，价格不占优势。技术方案评分相当，主要差距在价格分。建议后续项目在保证利润的前提下适当提高价格竞争力。",
    result_notes="折扣率报价项目，竞争激烈。",
)

# ---- 16. 未中标 - 陪标投标 ----
make_project(
    project_name="宁波市海曙区市政道路检测评估项目",
    bidding_type="public", status="lost",
    bidding_unit_id=3,  # 交通局（借用）
    region=json.dumps(["浙江省", "宁波市", "海曙区"]),
    manager_ids=json.dumps([3]),
    description="对海曙区主要市政道路进行检测评估，包含路面状况、桥梁结构安全、排水设施等检测内容。",
    agency_id=17, publish_platform_id=1,
    registration_deadline="2026-03-01", bid_deadline="2026-03-15",
    budget_amount=2500000, control_price_type="amount",
    control_price_upper=2400000, control_price_lower=2000000,
    bid_method="companion", partner_ids=json.dumps([14]),  # 正达检测（陪标对象）
    has_deposit=0, deposit_status="none",
    our_price=2350000,
    is_won=0,
    competitors=json.dumps([
        {"org_ids": [1], "price": 2350000, "score": 0, "is_shortlisted": False, "is_winning": False},
        {"org_ids": [14], "price": 2100000, "score": 0, "is_shortlisted": False, "is_winning": True},
    ]),
    winning_org_ids=json.dumps([14]),
    winning_org_id=14, winning_amount=2100000,
    lost_analysis="陪标项目，正达检测为预设中标单位。",
    result_notes="陪标完成。",
)

# ---- 17. 已流标 ----
make_project(
    project_name="衢州市大气环境在线监测系统扩建项目",
    bidding_type="public", status="failed_bid",
    bidding_unit_id=10,  # 生态环境局
    region=json.dumps(["浙江省", "衢州市", "衢江区"]),
    manager_ids=json.dumps([3, 4]),
    description="扩建大气环境在线监测系统，新增PM2.5、臭氧等监测站点及数据中心。",
    agency_id=18, publish_platform_id=1,
    tags=json.dumps(["环保", "监测"]),
    registration_deadline="2026-03-10", bid_deadline="2026-03-25",
    budget_amount=3200000, control_price_type="amount",
    control_price_upper=3000000, control_price_lower=2500000,
    bid_method="independent",
    has_deposit=1, deposit_status="paid",
    deposit_amount=60000, deposit_date="2026-03-12",
    our_price=2800000,
    result_deposit_status="returned", deposit_return_date="2026-04-08",
    is_won=0, is_bid_failed=1,
    competitors=json.dumps([
        {"org_ids": [1], "price": 2800000, "score": 0, "is_shortlisted": False, "is_winning": False},
        {"org_ids": [16], "price": 2750000, "score": 0, "is_shortlisted": False, "is_winning": False},
    ]),
    result_notes="因有效投标不足三家，本项目流标。保证金已退回。",
)

# ---- 18. 已放弃 - 从跟进中放弃 ----
make_project(
    project_name="丽水市智慧河湖长制管理平台项目",
    bidding_type="public", status="abandoned",
    bidding_unit_id=11,  # 农业局（借用）
    region=json.dumps(["浙江省", "丽水市", "青田县"]),
    manager_ids=json.dumps([4]),
    description="建设智慧河湖长制管理平台，实现河道巡查、水质监测、问题督办等数字化管理。",
    abandon_reason="经评估，项目技术要求超出我方目前能力范围，且需要水利行业专项资质，决定放弃跟进。",
)

# ---- 19. 已放弃 - 从已发公告放弃 ----
make_project(
    project_name="绍兴市柯桥区智慧社区综合服务平台项目",
    bidding_type="invited", status="abandoned",
    bidding_unit_id=5,  # 住建局
    region=json.dumps(["浙江省", "绍兴市", "柯桥区"]),
    manager_ids=json.dumps([2]),
    description="建设智慧社区综合服务平台，包含物业管理、社区安防、便民服务等功能模块。",
    agency_id=18, publish_platform_id=1,
    registration_deadline="2026-03-30", bid_deadline="2026-04-10",
    budget_amount=1800000, control_price_type="amount",
    control_price_upper=1700000, control_price_lower=1400000,
    abandon_reason="投标截止时间与我方另一重点项目冲突，人力不足，经内部讨论后决定放弃。",
)

# ---- 20. 入围分项 - 关联入围标(#14)，准备投标 ----
make_project(
    project_name="浙江省水利工程质量检测项目-杭嘉湖地区分项",
    bidding_type="prequalification", status="preparing",
    bidding_unit_id=8,  # 水利局
    region=json.dumps(["浙江省", "杭州市", "西湖区"]),
    manager_ids=json.dumps([1]),
    description="入围标杭嘉湖地区水利工程质量检测分项，从入围标项目同步参标单位。",
    parent_project_id=PARENT_PROJECT_ID,
    agency_id=17, publish_platform_id=1,
    tags=json.dumps(["水利", "检测", "入围分项"]),
    registration_deadline="2026-04-05", bid_deadline="2026-04-15",
    budget_amount=500000, control_price_type="amount",
    bid_specialist_id=2,
    bid_method="independent",
    has_deposit=0, deposit_status="none",
    our_price=480000,
    bid_notes="入围分项，参标单位从父项目同步。",
    competitors=json.dumps([
        {"org_ids": [1], "price": 0, "score": 0, "is_shortlisted": False, "is_winning": False},
        {"org_ids": [14], "price": 0, "score": 0, "is_shortlisted": False, "is_winning": False},
        {"org_ids": [15], "price": 0, "score": 0, "is_shortlisted": False, "is_winning": False},
    ]),
)

# ============================================================
# 提交 & 验证
# ============================================================
conn.commit()

print("\n=== 测试数据生成完成 ===\n")
cur.execute("SELECT id, project_name, status FROM project_infos")
for r in cur.fetchall():
    print(f"  #{r[0]:>2d} [{r[2]:<5s}] {r[1]}")

cur.execute("SELECT COUNT(*) FROM organizations")
print(f"\n单位总数: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM managers")
print(f"负责人总数: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM project_infos")
print(f"项目总数: {cur.fetchone()[0]}")

conn.close()
print("\n数据库已关闭。")
