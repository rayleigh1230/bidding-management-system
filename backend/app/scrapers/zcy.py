"""政采云（浙江企业采购信息服务网）scraper。

站点 URL: https://b.zhengcaiyun.cn
列表 API: POST https://b.zhengcaiyun.cn/portal/all  (覆盖所有子类)
反爬策略: 阿里云 WAF + Captcha Pro。

为什么用 CDP Runtime.evaluate：
  - 测试发现 Python requests + Chrome cookie 仍被 WAF 拦截（TLS 指纹/浏览器头不匹配）
  - 用 curl_cffi 同样被拦截
  - **唯一稳定方案：让调试 Chrome 自己 fetch，Python 通过 CDP 收 JSON**
  - Chrome 自动处理 TLS / sec-ch-ua / Accept-Encoding / cookie，WAF 全部识别为合法

为什么用 /portal/all 而不是 /portal/category：
  - /portal/category?categoryCode=ZcyAnnouncement2 只返回 4 种 pathName
    (询价/公开招标/竞争性谈判/竞争性磋商)，**漏抓 ZcyAnnouncement10007 / 10011 等子类**
  - /portal/all 是统一搜索接口，覆盖所有大类 × 子类，支持服务端日期过滤
  - 实测同一日：/portal/category=210 条 vs /portal/all=1112 条（5x 覆盖）

前置（用户操作）：
  1. 启动调试 Chrome：
     chrome.exe --remote-debugging-port=9222 --user-data-dir=C:/chrome-debug
  2. 在该 Chrome 中访问
     https://b.zhengcaiyun.cn/luban/search?k=&type=1
     如出现滑块手动通过（一般不会，新指纹不被识别）
  3. 抓取期间保持调试 Chrome 运行，页面 tab 不要关

cookie 失效或 WAF 重新触发 → 抛 SiteFetchError 让用户刷新页面。
"""
import json
import logging
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import websocket

from .base import (
    BaseScraper, ScrapeItem, SiteFetchError,
    is_result_announcement, extract_region_from_text,
)

logger = logging.getLogger(__name__)

CDP_HOST = "http://localhost:9222"
TARGET_DOMAIN = "b.zhengcaiyun.cn"
PAGE_URL = "https://b.zhengcaiyun.cn/luban/search?k=&type=1"
API_PATH = "/portal/all"  # 用相对路径让 Chrome 同源请求

PAGE_SIZE = 50
MAX_PAGES = 50  # 1112 条 / 50 ≈ 23 页，留余量

SHANGHAI_TZ = timezone(timedelta(hours=8))


# ---- CDP 浏览器交互 ----

def _list_cdp_targets() -> list:
    try:
        with urllib.request.urlopen(f"{CDP_HOST}/json", timeout=3) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data if isinstance(data, list) else []
    except Exception as e:
        raise SiteFetchError(
            f"zcy: 连不上 CDP {CDP_HOST} ({type(e).__name__})。"
            f"请确认已用 --remote-debugging-port=9222 启动调试 Chrome。"
        )


def _pick_page_ws(targets: list) -> str:
    """优先取政采云页面 tab；fallback 到任意 page tab。"""
    for t in targets:
        if (t.get("type") == "page"
                and TARGET_DOMAIN in (t.get("url") or "")
                and t.get("webSocketDebuggerUrl")):
            return t["webSocketDebuggerUrl"]
    for t in targets:
        if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
            return t["webSocketDebuggerUrl"]
    raise SiteFetchError(
        f"zcy: CDP 无可用 page 目标。请在调试 Chrome 中打开一个政采云页面。"
    )


def _cdp_eval(ws_url: str, js_expr: str, timeout: int = 30) -> str:
    """CDP Runtime.evaluate 执行 JS 表达式，返回值（字符串）。

    Chrome 111+ WebSocket 需要 suppress_origin 才能接受外部连接。
    """
    try:
        ws = websocket.create_connection(ws_url, timeout=timeout, suppress_origin=True)
    except Exception as e:
        raise SiteFetchError(f"zcy: CDP WebSocket 握手失败: {e}")
    try:
        ws.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": js_expr,
                "awaitPromise": True,
                "returnByValue": True,
                "timeout": timeout * 1000,
            },
        }))
        # 读响应（可能有多条事件，找到 id=1 的）
        deadline = timeout
        start = datetime.now().timestamp()
        while True:
            raw = ws.recv()
            resp = json.loads(raw)
            if resp.get("id") == 1:
                break
            if datetime.now().timestamp() - start > deadline:
                raise SiteFetchError("zcy: CDP evaluate 超时")
        err = resp.get("result", {}).get("exceptionDetails")
        if err:
            msg = err.get("exception", {}).get("description", str(err))
            raise SiteFetchError(f"zcy: 页面 JS 执行异常: {msg[:200]}")
        value = resp.get("result", {}).get("result", {}).get("value")
        if value is None:
            raise SiteFetchError(f"zcy: 页面 JS 返回空: {resp}")
        return value
    finally:
        ws.close()


# ---- Scraper ----

def _fetch_page_via_chrome(ws_url: str, body: dict) -> dict:
    """让 Chrome 在页面里 fetch /portal/all，返回 JSON dict。

    返回结构: {"success": true, "result": {"data": {"total": N, "data": [...]}}}
    若被 WAF 拦截（响应含 aliyun_waf_aa），抛 SiteFetchError。
    """
    body_js = json.dumps(body, ensure_ascii=False)
    js = (
        "(async () => {\n"
        f"  const r = await fetch({json.dumps(API_PATH)}, {{\n"
        "    method: 'POST',\n"
        "    headers: {'Content-Type': 'application/json;charset=UTF-8'},\n"
        f"    body: JSON.stringify({body_js}),\n"
        "    credentials: 'include',\n"
        "  });\n"
        "  const text = await r.text();\n"
        "  return JSON.stringify({\n"
        "    status: r.status,\n"
        "    contentType: r.headers.get('content-type') || '',\n"
        "    isWaf: text.includes('aliyun_waf_aa'),\n"
        "    text: text,\n"
        "  });\n"
        "})()"
    )
    raw = _cdp_eval(ws_url, js, timeout=30)
    result = json.loads(raw)  # JS 返回的 JSON 字符串

    if result.get("isWaf"):
        raise SiteFetchError(
            f"zcy: WAF 拦截（Chrome 内 fetch 也被挡）— "
            f"请在调试 Chrome 中刷新政采云页面，必要时重新过滑块。"
        )
    if not result.get("contentType", "").startswith("application/json"):
        raise SiteFetchError(
            f"zcy: 非 JSON 响应 (ct={result.get('contentType')[:50]})，"
            f"可能 WAF 升级或页面上下文丢失。"
        )
    try:
        return json.loads(result["text"])
    except Exception as e:
        raise SiteFetchError(f"zcy: JSON 解析失败: {e}, head={result['text'][:200]}")


class ZcyScraper(BaseScraper):
    name = "zcy"
    requires_playwright = False

    def fetch(self, day: date) -> list[dict]:
        """通过 CDP 让调试 Chrome 抓取政采云当日全部公告。

        /portal/all 支持服务端日期过滤，按 publishDateBegin/End 直接拿当日全量。
        覆盖所有子类（ZcyAnnouncement1~7, 10007, 10011 等），不漏抓。
        """
        targets = _list_cdp_targets()
        ws_url = _pick_page_ws(targets)

        day_start_ms = int(datetime.combine(
            day, datetime.min.time(), tzinfo=SHANGHAI_TZ
        ).timestamp() * 1000)
        day_end_ms = day_start_ms + 24 * 3600 * 1000

        records: list[dict] = []
        for page_idx in range(MAX_PAGES):
            body = {
                "keyword": "",
                "firstCode": "",       # 不限大类，覆盖全部
                "secondCode": "",      # 不限子类
                "districtCode": [],
                "publishDateBegin": day_start_ms,
                "publishDateEnd": day_end_ms,
                "pageNo": page_idx + 1,
                "pageSize": PAGE_SIZE,
                "isTitleSearch": 1,
                "order": "desc",
                "leaf": "0",
            }
            try:
                data = _fetch_page_via_chrome(ws_url, body)
            except SiteFetchError:
                raise  # 上抛让 scrape_runner 记 error_summary
            except Exception as e:
                logger.warning(f"zcy 第 {page_idx+1} 页异常: {e}")
                break

            items = data.get("result", {}).get("data", {}).get("data", []) or []
            if not items:
                break

            records.extend(items)

            total = data.get("result", {}).get("data", {}).get("total", 0)
            logger.info(
                f"zcy page {page_idx+1}: +{len(items)} (累计 {len(records)} / total={total})"
            )

            if len(records) >= total or len(items) < PAGE_SIZE:
                break

        return records

    def normalize(self, raw: dict) -> Optional[ScrapeItem]:
        title = (raw.get("title") or raw.get("projectName") or "").strip()
        if not title:
            return None
        if is_result_announcement(title):
            return None

        # 详情 URL：articleId 是 base64，需 URL-encode（== → %3D%3D, / → %2F）
        article_id = raw.get("articleId") or ""
        source_url = ""
        if article_id:
            encoded = urllib.parse.quote(article_id, safe="")
            source_url = f"https://b.zhengcaiyun.cn/luban/detail?articleId={encoded}"

        external_no = f"zcy_{article_id}" if article_id else None

        # publish_date（Unix ms → date）
        publish_date = None
        pub_ms = raw.get("publishDate")
        if isinstance(pub_ms, int):
            try:
                publish_date = datetime.fromtimestamp(
                    pub_ms / 1000, tz=SHANGHAI_TZ
                ).date()
            except Exception:
                pass

        bidding_unit_name = (raw.get("author")
                             or raw.get("purchaseName")
                             or "").strip() or None

        # 地区（districtName 示例 "浙江杭州" / "企采区本级"）
        # 用统一辅助函数提取，districtName 无效时回退到标题
        region_text = (raw.get("districtName") or "").strip()
        region = (
            extract_region_from_text(region_text)
            or extract_region_from_text(title)
        )

        # 公告类型 + 采购方式（pathName 形如 "公示公告 | 采购公告 | 公开招标公告"）
        path_name = (raw.get("pathName") or "").strip()
        proc_method = (raw.get("procurementMethod") or "").strip()
        desc_parts = [p.strip() for p in path_name.split("|") if p.strip()]
        if proc_method and proc_method not in desc_parts:
            desc_parts.append(proc_method)
        description = " / ".join(desc_parts) if desc_parts else None

        # 开标时间
        bid_deadline = None
        bo_ms = raw.get("bidOpeningTime")
        if isinstance(bo_ms, int):
            try:
                bid_deadline = datetime.fromtimestamp(
                    bo_ms / 1000, tz=SHANGHAI_TZ
                ).date()
            except Exception:
                pass

        return ScrapeItem(
            project_name=title,
            bidding_type="公开招标",
            bidding_unit_name=bidding_unit_name,
            publish_platform_name="浙江企业采购信息服务网",
            region=region,
            external_no=external_no,
            source_url=source_url,
            publish_date=publish_date,
            bid_deadline=bid_deadline,
            description=description,
        )
