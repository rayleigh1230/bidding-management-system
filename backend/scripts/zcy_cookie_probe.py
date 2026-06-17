"""政采云 CDP cookie 探查脚本。

前置：
  1. 关闭所有 Chrome 窗口
  2. 启动调试 Chrome（命令行或桌面快捷方式）：
     chrome.exe --remote-debugging-port=9222 --user-data-dir=C:/chrome-debug --remote-allow-origins=*
  3. 在调试 Chrome 里访问
     https://b.zhengcaiyun.cn/luban/category?isEnterpriseProvince=true&isState=true&parentId=550016&childrenCode=ZcyAnnouncement2
     手动过滑块验证（如果出现），确认能看到项目列表
  4. 保持调试 Chrome 打开，运行本脚本：
     python backend/scripts/zcy_cookie_probe.py

输出：
  - 读到的 cookie 数量与名称
  - 用 cookie 调 /portal/category 的响应（JSON / WAF 拦截 / 签名错误）
"""
import json
import time
import sys
import urllib.request
import urllib.error
from typing import Optional

import requests
import websocket  # websocket-client

CDP_HOST = "http://localhost:9222"
TARGET_DOMAIN = "b.zhengcaiyun.cn"
API_URL = "https://b.zhengcaiyun.cn/portal/category"
PAGE_URL = ("https://b.zhengcaiyun.cn/luban/category"
            "?isEnterpriseProvince=true&isState=true"
            "&parentId=550016&childrenCode=ZcyAnnouncement2")


def list_cdp_targets() -> list[dict]:
    """列出 Chrome 调试目标（打开的 tab）。"""
    try:
        with urllib.request.urlopen(f"{CDP_HOST}/json", timeout=3) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data if isinstance(data, list) else []
    except urllib.error.URLError as e:
        print(f"[ERROR] 连不上 {CDP_HOST} — {e}")
        print("请确认调试 Chrome 已启动：")
        print('  chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\\chrome-debug')
        sys.exit(1)


def pick_browser_ws(targets: list[dict]) -> str:
    """优先取 zhengcaiyun 页面的 WebSocket（Network domain 只在 page-level 可用）。"""
    # 1. 优先匹配 zhengcaiyun 的 page tab
    for t in targets:
        if (t.get("type") == "page"
                and "zhengcaiyun" in (t.get("url") or "")
                and t.get("webSocketDebuggerUrl")):
            return t["webSocketDebuggerUrl"]
    # 2. fallback: 任意 page tab
    for t in targets:
        if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
            return t["webSocketDebuggerUrl"]
    print("[ERROR] 没有可用的 page-level CDP 目标 — 请在调试 Chrome 里打开一个 zhengcaiyun 页面")
    sys.exit(1)


def cdp_get_all_cookies(ws_url: str) -> list[dict]:
    """通过 CDP Network.getAllCookies 读取浏览器所有 cookie。"""
    # Chrome 111+ 默认拒绝带 Origin 的 WebSocket 连接。
    # 解决：发送 Chrome 内置允许的 Origin（devtools://devtools），或空 Origin。
    try:
        ws = websocket.create_connection(
            ws_url, timeout=5, origin="devtools://devtools"
        )
    except Exception:
        # fallback: 试不带 Origin
        ws = websocket.create_connection(ws_url, timeout=5, suppress_origin=True)
    try:
        # Network.getAllCookies 不需要先 Network.enable，直接调即可
        payload = json.dumps({"id": 1, "method": "Network.getAllCookies", "params": {}})
        ws.send(payload)
        raw = ws.recv()
        resp = json.loads(raw)
        if "error" in resp:
            print(f"[ERROR] CDP 返回错误: {resp['error']}")
            sys.exit(1)
        return resp.get("result", {}).get("cookies", [])
    finally:
        ws.close()


def filter_zcy_cookies(all_cookies: list[dict]) -> list[dict]:
    """过滤 b.zhengcaiyun.cn 及父域的 cookie。"""
    keep = []
    for c in all_cookies:
        domain = (c.get("domain") or "").lstrip(".")
        if domain == TARGET_DOMAIN or domain.endswith("." + TARGET_DOMAIN) or TARGET_DOMAIN.endswith(domain):
            keep.append(c)
    return keep


def build_cookie_header(cookies: list[dict]) -> str:
    """把 CDP cookie 列表转成 Cookie header 字符串。"""
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get("name") and c.get("value"))


def call_api_with_cookies(cookie_header: str) -> dict:
    """用 cookie POST /portal/category，返回测试结果。"""
    ts = int(time.time() * 1000)
    body = {
        "pageNo": 1,
        "pageSize": 15,
        "categoryCode": "ZcyAnnouncement2",
        "_t": ts,
        "isEnterpriseProvince": True,
        "isState": True,
    }
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
    is_waf = "aliyun_waf_aa" in r.text
    is_json = "application/json" in r.headers.get("content-type", "")
    result = {
        "status": r.status_code,
        "is_waf": is_waf,
        "is_json": is_json,
        "len": len(r.text),
        "content_type": r.headers.get("content-type", ""),
        "head": r.text[:300],
    }
    if is_json:
        try:
            d = r.json()
            result["json_keys"] = list(d.keys())
            inner = d.get("result")
            if isinstance(inner, dict):
                result["result_keys"] = list(inner.keys())
                for k in ("data", "records", "list", "items", "rows"):
                    if k in inner:
                        items = inner[k]
                        result[f"result.{k}_count"] = len(items) if isinstance(items, list) else "n/a"
                        if isinstance(items, list) and items:
                            result["first_item_keys"] = list(items[0].keys())[:20]
                            result["first_item_sample"] = json.dumps(items[0], ensure_ascii=False)[:600]
                        break
            else:
                result["result_type"] = type(inner).__name__
        except Exception as e:
            result["parse_error"] = str(e)
    return result


def main():
    print(f"==== 1. 连接 CDP {CDP_HOST} ====")
    targets = list_cdp_targets()
    print(f"  找到 {len(targets)} 个调试目标")
    for t in targets[:5]:
        print(f"    - [{t.get('type')}] {t.get('title','')[:40]} | {t.get('url','')[:60]}")

    print()
    print("==== 2. 通过 CDP 读 cookie ====")
    ws_url = pick_browser_ws(targets)
    print(f"  WS: {ws_url[:80]}...")
    all_cookies = cdp_get_all_cookies(ws_url)
    print(f"  浏览器共 {len(all_cookies)} 条 cookie")

    zcy = filter_zcy_cookies(all_cookies)
    print(f"  其中 {TARGET_DOMAIN} 域名 {len(zcy)} 条:")
    for c in zcy:
        v = (c.get("value") or "")
        v_show = v[:30] + ("..." if len(v) > 30 else "")
        exp_ts = c.get("expires", -1)
        if exp_ts > 0:
            exp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(exp_ts))
        else:
            exp_str = "session"
        print(f"    {c.get('name')} = {v_show}  expires={exp_str}")

    if not zcy:
        print()
        print("[FAIL] 没有 zhengcaiyun 的 cookie — 请确认在调试 Chrome 里已访问过并通过验证")
        sys.exit(1)

    cookie_header = build_cookie_header(zcy)
    print()
    print(f"==== 3. 用 cookie POST {API_URL} ====")
    print(f"  Cookie header 长度: {len(cookie_header)}")
    result = call_api_with_cookies(cookie_header)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print()
    if result["is_json"] and not result["is_waf"]:
        if any(k.startswith("result.") and k.endswith("_count") for k in result):
            count_keys = [k for k in result if k.startswith("result.") and k.endswith("_count")]
            print(f"[OK] 成功拿到 JSON 列表数据 — {count_keys[0]} = {result[count_keys[0]]} 条")
        else:
            print("[?] 拿到 JSON 但找不到列表字段，看 result_keys 字段确认结构")
    elif result["is_waf"]:
        print("[FAIL] 仍被 WAF 拦截 — cookie 不够，可能还需要 WAF token（u_atoken/u_asig）")
    else:
        print(f"[FAIL] 未识别响应 — HTTP {result['status']}, ct={result['content_type']}")


if __name__ == "__main__":
    main()
