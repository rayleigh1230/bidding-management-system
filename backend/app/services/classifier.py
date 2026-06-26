"""Qwen LLM 项目分类器 — 判断公告是否属于工程检测类业务。

灰度 case（关键词分类返回 "grey"）由 scrape_runner 批量并发调用本模块。
复用 document_parser.py 的 DashScope OpenAI 兼容客户端配置。
"""
import json
import logging
from typing import Optional

from openai import OpenAI

from ..core.config import settings

logger = logging.getLogger(__name__)

# 内存缓存：external_no → ("white" | "reject", reason)
# 同一次 run 内避免重复调 LLM（同条公告可能在多次抓取间复用）
_CACHE: dict[str, tuple[str, str]] = {}

SYSTEM_PROMPT = """你是招标公告分类助手。判断这个项目的核心采购对象是不是「土木工程实体/设施的检测、监测、勘察、测绘、鉴定【服务】」。

注意：is_target=true 表示【我们应该去投这个标】，即这个项目采购的就是一份检测/监测/勘察/测绘/鉴定【服务】。

【判定为 true 的典型情况 — 无论项目位置在哪里，只要采购的是下列服务就是 true】
- 消防设施检测、消防设施维护检测（任何建筑的年度消防检测服务 → true）
- 防雷装置检测、防雷工程检测
- 建筑工程质量检测、主体结构检测、桩基检测、钢结构检测、幕墙检测
- 桥梁/道路/隧道的定期检查、荷载试验、竣工质量鉴定
- 室内空气质量检测、节能检测、保温检测
- 变形监测、沉降观测、基坑监测、边坡监测
- 工程勘察、岩土工程勘察、工程测绘、地形测量、地籍测绘
- 抗震鉴定、可靠性鉴定、房屋安全鉴定
- 排水管道 CCTV 检测、管道疏通检测

【判定为 false 的情况 — 即使标题含「检测/监测/鉴定」字样也要 false】

1. 采购检测/监测的【设备、装置、仪器、耗材、试剂】本身：
   检测装置采购、监测仪器采购、小棱镜采购、实验耗材采购、试剂采购、设备采购
   → 我们是检测服务商，不卖设备

2. 工业/化工/电力/特种设备检验（非土木工程）：
   常压储罐检验、压力管道检验、塔釜设备检验、锅炉检验、电梯检验
   化工管道检验、发电机组监测、变压器检测、机组运行监测报告
   → 工业设备，不是土木工程

3. 医学/司法/食品/车辆类：
   医疗器械检测、司法鉴定（含公安司法鉴定中心理化实验室耗材采购）、食品检测、血清检测、基因检测
   车辆尾气检测、移动机械尾气检测、心理健康评估

4. 建设/开发/设计类（建工程或做设计，不是做检测服务）：
   监测系统建设、监测能力提升项目建设、在线监测平台开发
   设计及评估、景观设计评估、可行性研究
   【特别注意】「勘察设计」组合出现时是设计合同，不是勘察服务 → false
   【特别注意】「设计采购」「设计施工」「EPC」「总承包」类合同 → false

5. 运维/养护中的非检测环节：
   设施维护保养、绿化养护、保洁保安、物业管理
   水资源计量监测例行维护服务、排水设施维护项目 → false（即便含「监测」「检测」字样）

6. 消防气体灭火系统类（充装/安装/维保，不是土木工程检测）：
   气体灭火系统瓶体检测、灭火剂补足服务、气体钢瓶充装检测、柜式气体灭火系统安装
   → 这是消防设备的充装/维保服务，不是建筑消防设施检测
   （区分：建筑年度「消防设施检测服务」「消防检测服务」→ true）

7. 环保 / 生态 / 环境监测类（我们不涉及）：
   海洋生态修复监测、养殖用海监测、生态环境局委托监测、水质监测、大气监测
   废气/废液/固废/危废处置与监测、水土保持监测、尾气检测、油气回收检测
   空气检测和治理、碳排放监测、污染源监测、环保检测服务
   → 这是环境监测/生态保护服务，不是土木工程实体检测 → false
   （区分：「建筑室内空气质量检测」「室内环境检测」属建筑节能验收 → true）

8. 地质灾害类（我们不涉及）：
   地质灾害危险性评估、地灾分区评估、地质灾害防治
   → 这是国土防灾服务，不是工程检测 → false

9. 城市管理服务外包类（不是检测）：
   市容秩序管理服务外包、城管服务、秩序管理服务
   → 这是城市管理外包服务，不是检测 → false

10. 海事/航运服务类（不是土木工程检测）：
    通航安全评估、航道评估、海事咨询
    → 这是航运/海事服务，不是码头结构检测 → false

11. 工业设施运营评估（非土木工程）：
    电厂灰库安全评估、油库安全评估、发电机组评估
    → 工业设备/工业场地评估，不是土木工程 → false

【关键判别问句】
这个项目最终交付的是不是一份【检测/监测/勘察/测绘/鉴定报告或服务】？
- 是 → is_target=true
- 交付的是设备/耗材/施工/设计/运维/软件 → is_target=false

请严格按以下 JSON 返回（无其他文字、无 markdown）：
{"is_target": true|false, "category": "建筑工程|桥梁工程|市政工程|交通工程|水利工程|防雷|消防|空气节能|智能化|勘察测绘|其他工程|非工程", "reason": "20字内"}
"""


class ProjectClassifier:
    """Qwen LLM 项目分类器（单例，由 get_classifier() 创建）。"""

    def __init__(self):
        if not settings.DASHSCOPE_API_KEY:
            raise RuntimeError("DASHSCOPE_API_KEY 未配置，无法初始化 LLM 分类器")
        self.client = OpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL,
            timeout=30,
        )
        self.model = settings.QWEN_CLASSIFIER_MODEL

    def classify(
        self,
        title: str,
        context: str = "",
        external_no: Optional[str] = None,
    ) -> tuple[str, str]:
        """返回 (decision, reason)。decision ∈ {"white", "reject"}。

        - external_no 给定时先查缓存
        - LLM 异常时 fallback 为 "white"（宁多抓不漏抓）
        """
        if external_no and external_no in _CACHE:
            return _CACHE[external_no]

        user_msg = f"标题：{title}\n上下文：{context[:200]}" if context else f"标题：{title}"
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = completion.choices[0].message.content if completion.choices else ""
            data = json.loads(raw) if raw else {}
            # 兼容新旧字段名：is_target（新）或 is_engineering（旧）
            is_eng = bool(data.get("is_target", data.get("is_engineering", False)))
            category = str(data.get("category", "")).strip()
            reason = str(data.get("reason", "")).strip()
            decision = "white" if is_eng else "reject"
            full_reason = f"[{category}] {reason}" if category else reason
        except Exception as e:
            logger.warning(
                f"LLM 分类失败 (title={title[:30]}): {e}，fallback=white"
            )
            decision, full_reason = "white", f"LLM 异常 fallback: {type(e).__name__}"

        if external_no:
            _CACHE[external_no] = (decision, full_reason)
        return decision, full_reason


_classifier_instance: Optional[ProjectClassifier] = None


def get_classifier() -> ProjectClassifier:
    """单例，避免重复初始化 OpenAI 客户端。"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ProjectClassifier()
    return _classifier_instance


def clear_cache():
    """清空内存缓存（测试用）。"""
    _CACHE.clear()
