import requests

JIRA_BASE_URL = "https://jira.mts.ru"
JIRA_TOKEN = "xxx"

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "Authorization": f"Bearer {JIRA_TOKEN}",
})

resp = session.get(f"{JIRA_BASE_URL}/rest/api/2/myself")

print("Status       :", resp.status_code)
print("Content-Type :", resp.headers.get("Content-Type"))
print("Body sample  :", resp.text[:500])

