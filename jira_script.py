import os
import json
from collections import defaultdict

import requests

# === НАСТРОЙКИ ДЛЯ ТВОЕЙ JIRA ===
JIRA_BASE_URL = "https://jira.mts.ru"
BOARD_ID      = 15999
PROJECT_KEY   = "MEDIADWH"

JIRA_USER  = "konstantav@mts.ru"   # например, "konstantav@mts.ru"
JIRA_TOKEN = "NDg4MTEzODg5NjU1Oh/TXjHNs1ShIEzNu5uCwRnijyuY"  # токен/пароль приложения

# Явный список спринтов (из твоих ссылок)
SPRINTS = [
    {"id": 49973, "name": "DWH Спринт 1"},
    {"id": 50967, "name": "DWH Спринт 2"},
    {"id": 51158, "name": "DWH Спринт 3"},
    {"id": 51363, "name": "DWH Спринт 4"},
    {"id": 51507, "name": "DWH Спринт 5"},
    {"id": 51672, "name": "DWH Спринт 6"},
    {"id": 51843, "name": "DWH Спринт 7"},
    {"id": 52011, "name": "DWH Спринт 8"},
]

# Порядок стримов в дашборде
STREAM_ORDER = [
    "Операционная деятельность",
    "Live",
    "Lakehouse",
    "Odin",
    "Рефакторинг телесмотрения",
    "Blender",
]

def get_stream_for_issue(issue):
    """
    Логика маппинга задачи к стриму.
    Здесь пример по labels — ты можешь поправить под себя.
    """
    fields = issue["fields"]
    labels = [l.lower() for l in (fields.get("labels") or [])]

    if any("live" in l for l in labels):
        return "Live"
    if any("lakehouse" in l or "kion" in l for l in labels):
        return "Lakehouse"
    if any("odin" in l for l in labels):
        return "Odin"
    if any("tvref" in l or "Рефакторинг телесмотрения" in l or "refactor_tv" in l for l in labels):
        return "Рефакторинг телесмотрения"
    if any("blender" in l for l in labels):
        return "Blender"

    # дефолт – операционка
    return "Операционная деятельность"


session = requests.Session()
session.auth = (JIRA_USER, JIRA_TOKEN)
session.headers.update({"Accept": "application/json"})


def get_issues_for_sprint(sprint_id: int):
    url = f"{JIRA_BASE_URL}/rest/api/2/search"

    # Статусы подставь свои, если отличаются
    jql_parts = [
        f"sprint = {sprint_id}",
        'status in ("Closed","Done","В работе","В анализе")',
        f'project = "{PROJECT_KEY}"',
    ]
    jql = " AND ".join(jql_parts)

    issues = []
    start_at = 0
    while True:
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": 100,
            "fields": ["summary", "status", "labels", "components"],
        }
        resp = session.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        issues.extend(data.get("issues", []))
        if start_at + data["maxResults"] >= data["total"]:
            break
        start_at += data["maxResults"]

    return issues


def aggregate_sprint(issues):
    counts = defaultdict(int)
    for issue in issues:
        stream = get_stream_for_issue(issue)
        counts[stream] += 1

    total = sum(counts.values()) or 1

    percentages = {
        stream: round(counts.get(stream, 0) * 100.0 / total, 2)
        for stream in STREAM_ORDER
    }
    return percentages, counts, total


def build_sprint_json(output_path="sprint_load.json"):
    labels = []
    data_by_stream = {s: [] for s in STREAM_ORDER}
    raw_counts = {s: [] for s in STREAM_ORDER}

    for s in SPRINTS:
        sprint_id = s["id"]
        raw_name  = s["name"]      # "DWH Спринт 1"
        # Можно оставить как есть, либо обрезать "DWH "
        sprint_name = raw_name.replace("DWH ", "")  # "Спринт 1"

        issues = get_issues_for_sprint(sprint_id)
        percents, counts, total = aggregate_sprint(issues)

        labels.append(sprint_name)
        for stream in STREAM_ORDER:
            data_by_stream[stream].append(percents.get(stream, 0.0))
            raw_counts[stream].append(counts.get(stream, 0))

    payload = {
        "labels": labels,
        "streams": STREAM_ORDER,
        "data": data_by_stream,
        "counts": raw_counts,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Saved sprint data to {output_path}")


if __name__ == "__main__":
    build_sprint_json()