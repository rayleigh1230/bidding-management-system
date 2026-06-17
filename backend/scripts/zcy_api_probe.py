"""政采云 API 字段深度探查：日期过滤 + 详情 URL + 完整字段结构。

复用 zcy_cookie_probe.py 的 CDP 读 cookie 逻辑。
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

import requests
import websocket

sys.path.insert(0, '.')
from scripts.zcy_cookie_probe import (
    list_cdp_targets, pick_browser_ws, cdp_get_all_cookies,
    filter_zcy_cookies, build_cookie_header, PAGE_URL, API_URL, TARGET_DOMAIN,
)


def fetch_page(cookie_header: str, body: dict) -> dict:
    """POST /portal/category 拿一页。"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://b.zhengcaiyun.cn",
        "Referer": PAGE_URL,
        "Cookie": cookie_header,
    }
    r = requests.post(API_URL, json=body, headers=headers, timeout=15)
    if "aliyun_waf_aa" in r.text:
        return {"_waf": True}
    return r.json()


def main():
    targets = list_cdp_targets()
    ws_url = pick_browser_ws(targets)
    cookies = filter_zcy_cookies(cdp_get_all_cookies(ws_url))
    if not cookies:
        print("[FATAL] 没有 zhengcaiyun cookie — 请确认调试 Chrome 已打开政采云页面")
        sys.exit(1)
    ch = build_cookie_header(cookies)
    print(f"cookie 长度: {len(ch)}\n")

    today = date.today()
    yesterday = today - timedelta(days=1)

    # ---- 测 1: 默认拿一页看完整字段 ----
    print("==== 测 1: 默认一页 ====")
    body = {
        "pageNo": 1, "pageSize": 5,
        "categoryCode": "ZcyAnnouncement2",
        "_t": int(time.time() * 1000),
        "isEnterpriseProvince": True, "isState": True,
    }
    d = fetch_page(ch, body)
    if d.get("_waf"):
        print("WAF 拦截"); return
    print(f"  total = {d.get('result',{}).get('data',{}).get('total')}")
    items = d.get("result", {}).get("data", {}).get("data", [])
    print(f"  本页 {len(items)} 条")
    if items:
        print(f"  首条完整字段:")
        first = items[0]
        for k, v in first.items():
            v_str = str(v)[:100] if v is not None else "None"
            print(f"    {k} = {v_str}")
        # 看 articleId / id 等可作去重 key 的字段
        print(f"\n  首条所有 '_id' / 'url' / 'code' 字段:")
        for k, v in first.items():
            if any(s in k.lower() for s in ("id", "code", "url", "path", "guid")):
                print(f"    {k} = {v}")

    # ---- 测 2: 日期过滤参数（多种命名试一遍）----
    print("\n==== 测 2: 服务端日期过滤参数 ====")
    today_str = today.strftime("%Y-%m-%d")
    yest_str = yesterday.strftime("%Y-%m-%d")
    candidates = [
        ("publishStartTime + publishEndTime", {"publishStartTime": f"{yest_str} 00:00:00", "publishEndTime": f"{today_str} 23:59:59"}),
        ("startTime + endTime", {"startTime": f"{yest_str} 00:00:00", "endTime": f"{today_str} 23:59:59"}),
        ("dateTime (range)", {"dateTime": [yest_str, today_str]}),
        ("publishTimeStart + publishTimeEnd", {"publishTimeStart": f"{yest_str} 00:00:00", "publishTimeEnd": f"{today_str} 23:59:59"}),
        ("startDate + endDate", {"startDate": yest_str, "endDate": today_str}),
    ]
    for name, extra in candidates:
        body = {
            "pageNo": 1, "pageSize": 5,
            "categoryCode": "ZcyAnnouncement2",
            "_t": int(time.time() * 1000),
            "isEnterpriseProvince": True, "isState": True,
            **extra,
        }
        d = fetch_page(ch, body)
        if d.get("_waf"):
            print(f"  [{name}] WAF 拦截"); continue
        total = d.get("result", {}).get("data", {}).get("total")
        items = d.get("result", {}).get("data", {}).get("data", [])
        # 检查首条日期
        first_date = None
        if items:
            for k in ("publishTime", "publishDate", "gmtCreate", "createTime", "addTime"):
                if items[0].get(k):
                    first_date = (k, items[0][k])
                    break
        print(f"  [{name}] total={total} 本页={len(items)} 首条日期={first_date}")

    # ---- 测 3: 详情 URL 规则（看 articleId 怎么拼）----
    print("\n==== 测 3: 详情 URL 拼接规则 ====")
    body = {
        "pageNo": 1, "pageSize": 3,
        "categoryCode": "ZcyAnnouncement2",
        "_t": int(time.time() * 1000),
        "isEnterpriseProvince": True, "isState": True,
    }
    d = fetch_page(ch, body)
    items = d.get("result", {}).get("data", {}).get("data", [])
    for i, it in enumerate(items):
        article_id = it.get("articleId", "")
        title = (it.get("title") or "")[:50]
        # articleId 是 base64，URL 里需要 encode（== 转 %3D%3D）
        encoded_id = urllib.parse.quote(article_id, safe="")
        print(f"  [{i}] title={title!r}")
        print(f"      articleId={article_id!r}")
        print(f"      encoded  ={encoded_id!r}")
        # 已知可能格式：
        print(f"      候选 URL: https://b.zhengcaiyun.cn/luban/detail/{encoded_id}")
        # 看是否有现成的 url 字段
        for k in ("url", "linkUrl", "detailUrl", "href"):
            if it.get(k):
                print(f"      原始 {k}: {it[k]}")

    # ---- 测 4: 看大翻页效率（pageNo=2 拿到的数据是否连续）----
    print("\n==== 测 4: 翻页一致性 ====")
    ids_p1 = []
    for page in (1, 2):
        body = {
            "pageNo": page, "pageSize": 50,
            "categoryCode": "ZcyAnnouncement2",
            "_t": int(time.time() * 1000),
            "isEnterpriseProvince": True, "isState": True,
        }
        d = fetch_page(ch, body)
        items = d.get("result", {}).get("data", {}).get("data", [])
        ids = [it.get("articleId") for it in items]
        if page == 1:
            ids_p1 = ids
        else:
            overlap = set(ids) & set(ids_p1)
            print(f"  page1={len(ids_p1)} page2={len(ids)} 重叠={len(overlap)}")
            print(f"  page1 首: {ids_p1[0] if ids_p1 else None}")
            print(f"  page2 首: {ids[0] if ids else None}")
        if items:
            print(f"  page{page} 首 publishTime: {items[0].get('publishTime')}")
            print(f"  page{page} 末 publishTime: {items[-1].get('publishTime')}")


if __name__ == "__main__":
    main()
