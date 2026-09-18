#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NodeSeek 站内通知 + 每日签到

功能：
- 私信 / 回复我 / @我 推送到 Telegram
- 默认忽略自己发出的私信
- 每日签到（成功只写日志，失败才通知）
- 冷启动静默记录存量，避免历史消息刷屏
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
import traceback
from datetime import date, datetime
from pathlib import Path

import yaml
from curl_cffi import requests as cffi_requests

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.yaml"

BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}

API_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Content-Type": "application/json",
    "Origin": "https://www.nodeseek.com",
    "Referer": "https://www.nodeseek.com/",
}

NOTIFY_ENDPOINTS = {
    "message": [
        "https://www.nodeseek.com/api/notification/message/list",
        "https://www.nodeseek.com/api/notification/message",
    ],
    "reply": [
        "https://www.nodeseek.com/api/notification/reply-to-me/list",
        "https://www.nodeseek.com/api/notification/reply-to-me",
        "https://www.nodeseek.com/api/notification/replyToMe",
    ],
    "at": [
        "https://www.nodeseek.com/api/notification/at-me/list",
        "https://www.nodeseek.com/api/notification/at-me",
        "https://www.nodeseek.com/api/notification/atMe",
    ],
}


def resolve_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


def load_json(path: Path, default):
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def save_json(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"找不到 {CONFIG_FILE}，请先执行: cp config.example.yaml config.yaml"
        )
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    if not isinstance(cfg, dict):
        raise ValueError("config.yaml 格式错误，根节点必须是对象")
    return cfg


def cookies_to_dict(cookies: list) -> dict:
    result = {}
    for item in cookies:
        if isinstance(item, dict) and "name" in item and "value" in item:
            result[item["name"]] = item["value"]
    return result


def load_cookies(path: Path) -> list:
    data = load_json(path, [])
    if isinstance(data, dict):
        return [{"name": k, "value": v} for k, v in data.items()]
    if isinstance(data, list):
        return data
    return []


def load_seen(path: Path) -> set[str]:
    return set(str(x) for x in load_json(path, []))


def save_seen(path: Path, seen: set[str]) -> None:
    items = sorted(seen)
    if len(items) > 5000:
        items = items[-5000:]
    save_json(path, items)


def esc_html(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def strip_html(text: str) -> str:
    if not text:
        return ""
    raw = str(text)
    out = []
    skip = False
    for ch in raw:
        if ch == "<":
            skip = True
            continue
        if ch == ">":
            skip = False
            continue
        if not skip:
            out.append(ch)
    return "".join(out).strip()


def send_telegram(cfg: dict, text: str) -> None:
    token = str((cfg.get("telegram") or {}).get("bot_token") or "")
    chat_id = str((cfg.get("telegram") or {}).get("chat_id") or "")
    if not token or not chat_id or token.startswith("YOUR_"):
        print("Telegram 未配置，跳过发送")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text[:4000],
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        import requests as std_requests

        resp = std_requests.post(url, json=payload, timeout=15)
        if resp.status_code != 200:
            print(f"Telegram 发送失败: {resp.status_code} {resp.text[:300]}")
    except Exception as exc:
        print(f"Telegram 异常: {exc}")


def notify_error(cfg: dict, title: str, detail: str) -> None:
    send_telegram(cfg, f"<b>{title}</b>\n\n<pre>{esc_html(detail[:3000])}</pre>")


def b64url_json(value: str):
    if not value:
        return None
    pad = "=" * ((4 - len(value) % 4) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(value + pad).decode("utf-8"))
    except Exception:
        return None


def get_my_identity(cfg: dict, cookies: list) -> tuple[str, str]:
    """优先解析 pjwt，失败再用配置兜底。"""
    cookie_map = cookies_to_dict(cookies)
    token = str(cookie_map.get("pjwt") or cookie_map.get("PJWT") or "")
    data = None
    if token:
        parts = token.split(".")
        if len(parts) >= 2:
            data = b64url_json(parts[1])
        if data is None:
            data = b64url_json(token)

    user_id = ""
    username = ""
    if isinstance(data, dict):
        user_id = str(data.get("id") or data.get("member_id") or data.get("user_id") or "").strip()
        username = str(
            data.get("name") or data.get("username") or data.get("member_name") or ""
        ).strip()

    ns_cfg = cfg.get("nodeseek") or {}
    if not user_id:
        user_id = str(ns_cfg.get("my_user_id") or "").strip()
    if not username:
        username = str(ns_cfg.get("my_username") or "").strip()
    return user_id, username


def norm_id(value) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        value = value.get("id") or value.get("member_id") or value.get("user_id") or ""
    return str(value).strip()


def is_outgoing_message(kind: str, item: dict, my_id: str, my_name: str) -> bool:
    if kind != "message" or not isinstance(item, dict):
        return False

    sender_id = norm_id(
        item.get("sender_id")
        or item.get("senderId")
        or item.get("from_id")
        or item.get("fromId")
        or item.get("from_user_id")
    )
    sender = (
        item.get("sender_name")
        or item.get("senderName")
        or item.get("sender")
        or item.get("fromUser")
        or item.get("author")
        or item.get("username")
        or item.get("userName")
        or ""
    )
    if isinstance(sender, dict):
        sender_id = sender_id or norm_id(sender)
        sender = sender.get("name") or sender.get("username") or sender.get("member_name") or ""
    sender_name = str(sender).strip()

    if my_id and sender_id and sender_id == my_id:
        return True
    if my_name and sender_name and sender_name.lower() == my_name.lower():
        return True
    return False


def impersonate_of(cfg: dict) -> str:
    return str((cfg.get("nodeseek") or {}).get("impersonate") or "chrome124")


def check_cookie_valid(cfg: dict, cookies: list) -> bool:
    try:
        resp = cffi_requests.get(
            "https://www.nodeseek.com/notification",
            cookies=cookies_to_dict(cookies),
            headers=BROWSER_HEADERS,
            impersonate=impersonate_of(cfg),
            timeout=20,
        )
        if resp.status_code != 200:
            return False
        text = resp.text.lower()
        if "login" in resp.url.lower() or "请先登录" in resp.text or "sign in" in text:
            return False
        if "just a moment" in text:
            return False
        return True
    except Exception as exc:
        print(f"Cookie 检测异常: {exc}")
        return False


def do_daily_checkin(cfg: dict, cookies: list) -> tuple[bool, str]:
    random_flag = "true" if (cfg.get("checkin") or {}).get("random") else "false"
    url = f"https://www.nodeseek.com/api/attendance?random={random_flag}"
    headers = {
        **API_HEADERS,
        "Content-Type": "text/plain;charset=UTF-8",
        "Referer": "https://www.nodeseek.com/board",
        "Content-Length": "0",
    }
    try:
        resp = cffi_requests.post(
            url,
            data="",
            cookies=cookies_to_dict(cookies),
            headers=headers,
            impersonate=impersonate_of(cfg),
            timeout=20,
        )
        try:
            data = resp.json()
        except Exception:
            data = {}
        msg = data.get("message") or data.get("msg") or resp.text[:200]
        success = data.get("success")
        if success is True or success == "true" or "鸡腿" in str(msg) or "签到成功" in str(msg):
            return True, str(msg)
        if "已完成签到" in str(msg) or "请勿重复" in str(msg):
            return True, str(msg)
        if resp.status_code == 200 and ("成功" in str(msg) or data.get("status") == 0):
            return True, str(msg)
        return False, f"status={resp.status_code} msg={msg}"
    except Exception as exc:
        return False, str(exc)


def maybe_daily_checkin(cfg: dict, cookies: list, cookie_ok: bool, state_file: Path) -> None:
    checkin_cfg = cfg.get("checkin") or {}
    if not checkin_cfg.get("enabled", True) or not cookie_ok:
        return

    today = date.today().isoformat()
    last = load_json(state_file, {}).get("last_date", "")
    if last == today:
        return
    if datetime.now().hour < int(checkin_cfg.get("hour", 8)):
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始每日签到...")
    ok, msg = do_daily_checkin(cfg, cookies)
    if ok:
        save_json(state_file, {"last_date": today})
        print(f"签到成功: {msg}")
    else:
        print(f"签到失败: {msg}")
        notify_error(cfg, "每日签到失败", msg)


def item_id(kind: str, item: dict) -> str:
    stable = (
        item.get("id")
        or item.get("notificationId")
        or item.get("msgId")
        or item.get("max_id")
        or item.get("message_id")
        or item.get("comment_id")
    )
    if stable is not None and str(stable).strip() != "":
        return f"{kind}:{stable}"

    raw = "|".join([
        kind,
        str(item.get("sender_id") or item.get("from_id") or ""),
        str(item.get("receiver_id") or ""),
        str(
            item.get("createTime")
            or item.get("createdAt")
            or item.get("created_at")
            or item.get("time")
            or ""
        ),
        str(item.get("content") or item.get("message") or item.get("title") or "")[:120],
    ])
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def fetch_notify_list(url: str, cfg: dict, cookies: list) -> list:
    try:
        resp = cffi_requests.get(
            url,
            cookies=cookies_to_dict(cookies),
            headers=API_HEADERS,
            impersonate=impersonate_of(cfg),
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        for key in ("data", "list", "msgArray", "notifications", "items", "records"):
            if isinstance(data.get(key), list):
                return data[key]
        if isinstance(data, list):
            return data
        return []
    except Exception as exc:
        print(f"获取通知失败 {url}: {exc}")
        return []


def format_notify(kind: str, item: dict) -> str:
    label = {"message": "私信", "reply": "回复我的", "at": "@我"}.get(kind, kind)
    title = item.get("title") or item.get("subject") or ""
    content = item.get("content") or item.get("message") or item.get("text") or item.get("body") or ""
    author = (
        item.get("author")
        or item.get("username")
        or item.get("fromUser")
        or item.get("sender")
        or item.get("sender_name")
        or item.get("userName")
        or ""
    )
    if isinstance(author, dict):
        author = author.get("name") or author.get("username") or ""

    link = item.get("link") or item.get("url") or ""
    if not link and item.get("postId"):
        link = f"https://www.nodeseek.com/post-{item['postId']}-1"
    if not link and item.get("post_id"):
        link = f"https://www.nodeseek.com/post-{item['post_id']}-1"

    parts = [f"<b>NodeSeek {label}</b>", ""]
    if author:
        parts.append(f"<b>来自：</b>{esc_html(author)}")
    if title:
        parts.append(f"<b>标题：</b>{esc_html(title)}")
    content_short = strip_html(str(content))[:300]
    if content_short:
        parts.append(f"<b>内容：</b>\n{esc_html(content_short)}")
    if link:
        parts.append(f'\n<a href="{link}">查看</a>')
    return "\n".join(parts)


def enabled_kinds(cfg: dict) -> list[str]:
    notify_cfg = cfg.get("notify") or {}
    mapping = {
        "message": notify_cfg.get("private_message", True),
        "reply": notify_cfg.get("reply_to_me", True),
        "at": notify_cfg.get("at_me", True),
    }
    return [kind for kind, enabled in mapping.items() if enabled]


def check_site_notifications(cfg: dict, cookies: list, seen: set[str], seen_file: Path) -> set[str]:
    notify_cfg = cfg.get("notify") or {}
    bootstrap = len(seen) == 0 or bool(notify_cfg.get("force_bootstrap"))
    skip_outgoing = bool(notify_cfg.get("skip_outgoing_pm", True))
    my_id, my_name = get_my_identity(cfg, cookies)

    new_seen = set(seen)
    pushed = 0
    skipped_out = 0

    for kind in enabled_kinds(cfg):
        items = []
        for url in NOTIFY_ENDPOINTS[kind]:
            items = fetch_notify_list(url, cfg, cookies)
            if items:
                break

        for item in items[:50]:
            if not isinstance(item, dict):
                continue
            iid = item_id(kind, item)
            if iid in new_seen:
                continue
            new_seen.add(iid)

            if bootstrap:
                continue

            if skip_outgoing and is_outgoing_message(kind, item, my_id, my_name):
                skipped_out += 1
                print("跳过自己发出的私信")
                continue

            send_telegram(cfg, format_notify(kind, item))
            pushed += 1
            print(f"已推送新通知: {kind}")

    if new_seen != seen:
        save_seen(seen_file, new_seen)

    if bootstrap:
        print(f"冷启动：已静默记录 {len(new_seen)} 条，不推送")
    else:
        if pushed:
            print(f"本轮推送 {pushed} 条")
        if skipped_out:
            print(f"本轮跳过自己发出的私信 {skipped_out} 条")

    return new_seen


def main() -> None:
    cfg = load_config()
    ns_cfg = cfg.get("nodeseek") or {}
    path_cfg = cfg.get("paths") or {}
    interval_cfg = cfg.get("intervals") or {}

    cookie_file = resolve_path(ns_cfg.get("cookie_file") or "cookies.json")
    seen_file = resolve_path(path_cfg.get("notify_seen_file") or "notify_seen.json")
    checkin_file = resolve_path(path_cfg.get("checkin_state_file") or "checkin_state.json")

    cookie_interval = int(interval_cfg.get("cookie_check") or 3600)
    notify_interval = int(interval_cfg.get("notify_check") or 60)
    loop_sleep = int(interval_cfg.get("loop_sleep") or 30)

    print("=" * 60)
    print("NodeSeek 通知/签到脚本启动")
    print(f"配置文件: {CONFIG_FILE}")
    print(f"Cookie 文件: {cookie_file}")
    print("=" * 60)
    send_telegram(cfg, "NodeSeek 通知/签到监控已启动")

    cookies = load_cookies(cookie_file)
    if not cookies:
        notify_error(cfg, "启动失败", "cookies.json 为空或不存在")
        raise SystemExit("无 Cookie，退出")

    seen = load_seen(seen_file)
    last_cookie_check = 0.0
    last_notify_check = 0.0
    last_cookie_ok = None
    last_cookie_fail_notify = 0.0
    cookie_ok = False

    while True:
        try:
            now = time.time()

            if now - last_cookie_check >= cookie_interval or last_cookie_ok is None:
                cookies = load_cookies(cookie_file)
                cookie_ok = check_cookie_valid(cfg, cookies)
                last_cookie_check = now
                ts = datetime.now().strftime("%H:%M:%S")
                if cookie_ok:
                    print(f"[{ts}] Cookie 有效")
                    if last_cookie_ok is False:
                        send_telegram(cfg, "Cookie 已恢复有效")
                    last_cookie_ok = True
                else:
                    print(f"[{ts}] Cookie 无效或过期")
                    if last_cookie_ok is not False or (now - last_cookie_fail_notify) >= cookie_interval:
                        send_telegram(cfg, "NodeSeek Cookie 可能已过期，请重新导出 cookies.json")
                        last_cookie_fail_notify = now
                    last_cookie_ok = False

            maybe_daily_checkin(cfg, cookies, cookie_ok, checkin_file)

            if cookie_ok and (now - last_notify_check) >= notify_interval:
                seen = check_site_notifications(cfg, cookies, seen, seen_file)
                last_notify_check = now

            time.sleep(max(5, min(loop_sleep, notify_interval)))

        except KeyboardInterrupt:
            print("已停止")
            send_telegram(cfg, "NodeSeek 通知/签到监控已手动停止")
            break
        except Exception as exc:
            print(f"主循环出错: {exc}")
            notify_error(cfg, "通知脚本主循环异常", traceback.format_exc())
            time.sleep(30)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        try:
            notify_error(load_config(), "通知脚本致命错误，已退出", traceback.format_exc())
        except Exception:
            pass
        raise
