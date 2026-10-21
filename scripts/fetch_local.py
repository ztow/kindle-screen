#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读本机「日历」最近 4 条日程 + 「提醒事项 / 待办」未完成项 -> data/local.json
写完自动 git 提交推送（GitHub Pages 需要文件进仓库才能被页面读到）。
由 launchd 定时执行（北京时间 0/3/6/9/12/15/18/21 点整），也可手动跑。
"""
import base64
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "data" / "local.json"
CST = timezone(timedelta(hours=8))

REMINDER_LIST = "待办"   # 提醒事项里的列表名
MAX_EVENTS = 4
OBFUSCATE = True         # True = base64 包一层再落盘（页面自动识别明文/base64 两种）

CAL_SCRIPT = """
tell application "Calendar"
  set nowSecs to (do shell script "date +%s") as integer
  set out to ""
  repeat with c in calendars
    repeat with e in (every event of c whose start date >= (current date))
      set t to summary of e
      if t is missing value then set t to ""
      set s to start date of e
      set es to (s - (current date)) + nowSecs
      set ad to allday event of e
      set out to out & es & tab & (ad as string) & tab & t & linefeed
    end repeat
  end repeat
  return out
end tell
"""

REM_SCRIPT = """
tell application "Reminders"
  set nowSecs to (do shell script "date +%s") as integer
  set out to ""
  repeat with r in (every reminder of list "__LIST__" whose completed is false)
    set nm to name of r
    if nm is missing value then set nm to ""
    set dd to due date of r
    if dd is missing value then
      set out to out & nm & linefeed
    else
      set out to out & nm & tab & ((dd - (current date)) + nowSecs) & linefeed
    end if
  end repeat
  return out
end tell
"""

WK = ["一", "二", "三", "四", "五", "六", "日"]


def run_as(script):
    proc = subprocess.run(["osascript", "-e", script],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip()[:400])
    return proc.stdout


def read_events():
    events = []
    for line in run_as(CAL_SCRIPT).splitlines():
        parts = line.split("\t")
        if len(parts) < 3 or not parts[0].strip():
            continue
        try:
            epoch = int(float(parts[0].strip()))
        except ValueError:
            continue
        events.append({
            "epoch": epoch,
            "allday": parts[1].strip() == "true",
            "title": parts[2].strip(),
        })
    events.sort(key=lambda e: e["epoch"])
    out = []
    for e in events[:MAX_EVENTS]:
        dt = datetime.fromtimestamp(e["epoch"])
        when = "%02d/%02d 周%s %s" % (
            dt.month, dt.day, WK[dt.weekday()],
            "全天" if e["allday"] else "%02d:%02d" % (dt.hour, dt.minute))
        out.append({"label": when, "title": e["title"]})
    return out


def read_todos():
    todos = []
    for line in run_as(REM_SCRIPT.replace("__LIST__", REMINDER_LIST)).splitlines():
        parts = line.split("\t")
        title = parts[0].strip()
        if not title:
            continue
        due = ""
        if len(parts) > 1 and parts[1].strip():
            try:
                dt = datetime.fromtimestamp(int(float(parts[1].strip())))
                due = "%02d/%02d" % (dt.month, dt.day)
            except ValueError:
                due = ""
        todos.append({"title": title, "due": due})
    return todos


def write(data):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OBFUSCATE:
        raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        OUT.write_text(base64.b64encode(raw.encode("utf-8")).decode("ascii"),
                       encoding="utf-8")
    else:
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                       encoding="utf-8")


def git(*args):
    return subprocess.run(["git", "-C", str(BASE)] + list(args),
                          capture_output=True, text=True)


def push():
    if os.environ.get("KINDLE_NO_PUSH") == "1":
        print("KINDLE_NO_PUSH=1，跳过提交")
        return
    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        print("不在 git 仓库里，跳过提交")
        return
    git("add", "data/local.json")
    if git("diff", "--staged", "--quiet").returncode == 0:
        print("local.json 无变化，跳过提交")
        return
    msg = "chore: update local data " + datetime.now().strftime("%Y-%m-%d %H:%M")
    if git("commit", "-m", msg).returncode != 0:
        print("commit 失败")
        return
    pull = git("pull", "--rebase")
    if pull.returncode != 0:
        git("rebase", "--abort")
        print("pull --rebase 失败，请手动进仓库处理")
        return
    res = git("push")
    print("push 完成" if res.returncode == 0 else "push 失败：" + (res.stderr or "")[:300])


def main():
    data = {
        "generated_at": datetime.now(CST).strftime("%Y-%m-%d %H:%M"),
        "events": read_events(),
        "todos": read_todos(),
    }
    write(data)
    print("written %s | events=%d todos=%d" % (OUT, len(data["events"]), len(data["todos"])))
    push()


if __name__ == "__main__":
    main()
