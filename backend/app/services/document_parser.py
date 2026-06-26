"""阿里云 Qwen-Long 文档解析服务。

通过 DashScope 的 OpenAI 兼容模式上传招标文件并提取结构化字段。
"""
import json
import re
from typing import Optional

from openai import OpenAI

from ..core.config import settings


class DocumentParseError(Exception):
    """文档解析异常，携带 code 用于上层映射 HTTP 状态。"""

    def __init__(self, message: str, code: str = "parse_failed"):
        super().__init__(message)
        self.code = code


# 中文别名 → 标准化英文字段名
FIELD_ALIASES = {
    "项目名称": "project_name",
    "招标单位": "bidding_unit_name",
    "招标人": "bidding_unit_name",
    "采购单位": "bidding_unit_name",
    "采购人": "bidding_unit_name",
    "代理单位": "agency_name",
    "代理机构": "agency_name",
    "发布平台": "publish_platform_name",
    "交易平台": "publish_platform_name",
    "招标类型": "bidding_type",
    "所属地区": "region_text",
    "项目所在地": "region_text",
    "报名截止时间": "registration_deadline",
    "报名截止": "registration_deadline",
    "投标截止时间": "bid_deadline",
    "投标截止": "bid_deadline",
    "开标时间": "bid_deadline",
    "预算金额": "budget_amount",
    "项目预算": "budget_amount",
    "控制价类型": "control_price_type",
    "控制价上限": "control_price_upper",
    "控制价下限": "control_price_lower",
    "是否资格预审": "is_prequalification",
    "是否入围标": "is_prequalification",
    "标签": "tags",
    "备注": "bidding_notes",
    "是否有投标保证金": "has_deposit",
    "保证金金额": "deposit_amount",
}

SYSTEM_PROMPT = (
    "你是一个招标公告解析助手。请从用户上传的招标文件中提取以下结构化字段，"
    "并以严格 JSON 格式返回（不要任何解释文字、不要 markdown 代码块）。\n"
    "字段约定：\n"
    "  - 项目名称: string\n"
    "  - 招标单位: string（招标人/采购人）\n"
    "  - 代理单位: string（代理机构）\n"
    "  - 发布平台: string（公告发布的交易平台）\n"
    "  - 招标类型: 公开招标 | 邀请招标 | 中介超市\n"
    "  - 所属地区: string（如：浙江省杭州市西湖区）\n"
    "  - 报名截止时间: YYYY-MM-DD\n"
    "  - 投标截止时间: YYYY-MM-DD\n"
    "  - 预算金额: 数字（单位元，不含千分位）\n"
    "  - 控制价类型: 金额 | 折扣率 | 下浮率\n"
    "  - 控制价上限: 数字\n"
    "  - 控制价下限: 数字\n"
    "  - 是否资格预审: true | false（注意：此项同时表示「是否入围标」。"
    "    若文件出现「入围」「入围标」「短名单」「资格预审」「合格供应商库」「框架协议」「入围候选人」"
    "等任一特征，则填 true；普通招标项目填 false）\n"
    "  - 标签: string[]（如 ['工程','检测']）\n"
    "  - 备注: string\n"
    "  - 是否有投标保证金: true | false（按招标文件是否要求提交投标保证金判定）\n"
    "  - 保证金金额: 数字（单位元，不要求保证金时填 null）\n"
    "规则：找不到的字段填 null；日期必须 YYYY-MM-DD；金额只填数字不含单位。"
)


# 中标结果模式专用：中标候选人子字段别名（嵌套结构，处理 candidates 数组里每项的字段名）
RESULT_CANDIDATE_ALIASES = {
    "排名": "rank",
    "单位名称": "org_names",
    "中标单位": "org_names",
    "投标人": "org_names",
    "报价": "price",
    "投标报价": "price",
    "中标价": "price",
    "综合得分": "score",
    "得分": "score",
    "是否中标": "is_winning",
    "中标": "is_winning",
}

# 中标结果模式顶层字段别名
RESULT_TOP_ALIASES = {
    "中标候选人": "candidates",
    "候选人": "candidates",
    "合同编号": "contract_number",
    "合同金额": "contract_amount",
    "中标金额": "contract_amount",
    "备注": "result_notes",
    "说明": "result_notes",
}


def _build_result_prompt(control_price_type: Optional[str]) -> str:
    """构造中标公告解析 prompt。control_price_type 用于告知 LLM 报价单位。"""
    if control_price_type == "折扣率":
        unit_hint = "百分数值（如 95.5 表示九五折）"
    elif control_price_type == "下浮率":
        unit_hint = "下浮百分数值（如 5.0 表示下浮 5%）"
    else:
        unit_hint = "金额（单位元，不含千分位）"
    return (
        "你是一个中标公告/中标结果公示解析助手。请从用户上传的文件中提取以下结构化字段，"
        "并以严格 JSON 格式返回（不要任何解释文字、不要 markdown 代码块）。\n"
        "字段约定：\n"
        "  - 中标候选人: array of objects，按排名顺序，每项包含：\n"
        "      - 排名: number (1=第一中标候选人)\n"
        "      - 单位名称: string（联合体用顿号/逗号分隔多个单位）\n"
        f"      - 报价: number（{unit_hint}）\n"
        "      - 综合得分: number\n"
        "      - 是否中标: boolean（公示的最终中标人为 true，其余 false；入围标可多个 true）\n"
        "  - 合同编号: string（中标通知书中可能有）\n"
        "  - 合同金额: number（单位元，可能等于中标人报价）\n"
        "  - 备注: string\n"
        "规则：找不到的字段填 null；金额只填数字不含千分位；候选人按排名顺序输出；"
        "若无中标人（流标）则返回空数组。"
    )


class QwenLongParser:
    def __init__(self):
        if not settings.DASHSCOPE_API_KEY:
            raise DocumentParseError(
                "DASHSCOPE_API_KEY 未配置，请在 backend/.env 中设置", "config_missing"
            )
        self.client = OpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL,
            timeout=settings.QWEN_LONG_TIMEOUT,
        )

    def upload_file(self, file_path: str) -> str:
        """上传本地文件到 DashScope，返回 file_id。"""
        with open(file_path, "rb") as f:
            resp = self.client.files.create(file=f, purpose="file-extract")
        if not getattr(resp, "id", None):
            raise DocumentParseError("文件上传失败：阿里云未返回 file_id", "upload_failed")
        return resp.id

    def parse(
        self,
        file_id: str,
        parse_type: str = "bidding",
        control_price_type: Optional[str] = None,
    ) -> dict:
        """对已上传的文件进行字段抽取。

        parse_type:
            - "bidding"：招标公告，返回招标字段
            - "result"：中标公告/中标结果，返回候选人 + 合同字段
        """
        if parse_type == "result":
            prompt = _build_result_prompt(control_price_type)
            user_msg = "请提取上述中标公告/中标结果文件中的所有字段，并以 JSON 格式输出。"
        else:
            prompt = SYSTEM_PROMPT
            user_msg = "请提取上述招标文件中的所有字段，并以 JSON 格式输出。"

        try:
            completion = self.client.chat.completions.create(
                model=settings.QWEN_LONG_MODEL,
                messages=[
                    {"role": "system", "content": f"fileid://{file_id}"},
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            raise DocumentParseError(f"调用 Qwen-Long 失败: {e}", "api_error") from e

        raw = completion.choices[0].message.content if completion.choices else ""
        return self._normalize(raw, parse_type)

    def _normalize(self, raw: str, parse_type: str = "bidding") -> dict:
        if not raw:
            raise DocumentParseError("LLM 返回空内容", "invalid_response")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", raw)
            if not m:
                raise DocumentParseError(
                    "LLM 返回的内容不是合法 JSON", "invalid_response"
                )
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError as e:
                raise DocumentParseError(
                    f"LLM 返回的内容不是合法 JSON: {e}", "invalid_response"
                )

        if parse_type == "result":
            return self._normalize_result(data)
        return self._normalize_bidding(data)

    def _normalize_bidding(self, data: dict) -> dict:
        normalized: dict = {}
        for k, v in data.items():
            if v is None:
                continue
            key = str(k).strip()
            target = FIELD_ALIASES.get(key, key)
            if target not in normalized:
                normalized[target] = v

        # tags 容错：字符串拆分为数组
        tags = normalized.get("tags")
        if isinstance(tags, str):
            normalized["tags"] = [
                t.strip() for t in re.split(r"[,，;；]", tags) if t.strip()
            ]
        elif tags is not None and not isinstance(tags, list):
            normalized["tags"] = []

        return normalized

    def _normalize_result(self, data: dict) -> dict:
        """中标结果模式：归一化顶层字段 + candidates 嵌套数组。"""
        normalized: dict = {}
        for k, v in data.items():
            if v is None:
                continue
            key = str(k).strip()
            target = RESULT_TOP_ALIASES.get(key, key)
            if target not in normalized:
                normalized[target] = v

        # 处理 candidates 嵌套数组
        raw_candidates = normalized.get("candidates")
        if not isinstance(raw_candidates, list):
            # 容错：若 LLM 把单个候选人作为对象返回，包装成数组
            if isinstance(raw_candidates, dict):
                raw_candidates = [raw_candidates]
            else:
                raw_candidates = []

        cleaned: list[dict] = []
        for item in raw_candidates:
            if not isinstance(item, dict):
                continue
            entry: dict = {}
            for ck, cv in item.items():
                if cv is None:
                    continue
                ckey = str(ck).strip()
                ctarget = RESULT_CANDIDATE_ALIASES.get(ckey, ckey)
                if ctarget not in entry:
                    entry[ctarget] = cv
            # 单位名称可能是字符串或数组，统一成数组方便后端拆分匹配
            if "org_names" in entry and isinstance(entry["org_names"], str):
                names_str = entry["org_names"]
                entry["org_names"] = [
                    s.strip()
                    for s in re.split(r"[、,，;；/]", names_str)
                    if s.strip()
                ]
            if entry:
                cleaned.append(entry)

        normalized["candidates"] = cleaned
        return normalized


_parser_instance: Optional[QwenLongParser] = None


def get_parser() -> QwenLongParser:
    """单例，避免重复初始化 OpenAI 客户端。"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = QwenLongParser()
    return _parser_instance
