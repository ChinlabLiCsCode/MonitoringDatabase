#!/usr/bin/env python3
"""Push lab-monitoring-cloud.json to Grafana Cloud via the Grafana HTTP API.

Usage:
  python push_cloud_dashboard.py           — push the dashboard JSON
  python push_cloud_dashboard.py --list    — list all dashboards on your cloud account
  python push_cloud_dashboard.py --uid UID — push and overwrite a specific dashboard UID

Required .env variables:
  GRAFANA_CLOUD_URL     e.g. https://chinlablics.grafana.net
  GRAFANA_CLOUD_API_KEY service account token with Editor role

The script auto-discovers the real Prometheus datasource UID from the Grafana
Cloud instance and substitutes it into the dashboard JSON before pushing, so the
hardcoded placeholder in the JSON file never needs to be manually updated.
"""

import json
import os
import sys
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_PATH = os.path.join(SCRIPT_DIR, "grafana", "dashboards", "lab-monitoring-cloud.json")

# Placeholder UID used throughout the dashboard JSON. At push time this is
# replaced with the actual UID discovered from the Grafana Cloud instance.
PROM_PLACEHOLDER = "grafanacloud-chinlablics-prom"


def load_env(path: str) -> None:
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
    except FileNotFoundError:
        pass


def api_get(grafana_url: str, api_key: str, path: str) -> object:
    req = urllib.request.Request(
        grafana_url.rstrip("/") + path,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def resolve_prometheus_uid(grafana_url: str, api_key: str) -> str:
    """Return the actual UID of the Prometheus datasource in this Grafana instance.

    Tries to match by the placeholder name first, then falls back to the first
    datasource of type 'prometheus'.  Returns the placeholder unchanged if the
    API call fails or no match is found.
    """
    try:
        datasources = api_get(grafana_url, api_key, "/api/datasources")
    except Exception as exc:
        print(f"Warning: could not fetch datasources ({exc}); using placeholder UID.", file=sys.stderr)
        return PROM_PLACEHOLDER

    # Prefer a datasource whose name matches our placeholder (common in Grafana Cloud)
    for ds in datasources:
        if ds.get("name") == PROM_PLACEHOLDER:
            return ds["uid"]

    # Fall back to the first Prometheus-type datasource
    for ds in datasources:
        if ds.get("type") == "prometheus":
            return ds["uid"]

    print("Warning: no Prometheus datasource found; using placeholder UID.", file=sys.stderr)
    return PROM_PLACEHOLDER


def list_dashboards(grafana_url: str, api_key: str) -> None:
    items = api_get(grafana_url, api_key, "/api/search?type=dash-db")
    if not items:
        print("No dashboards found.")
        return
    print(f"{'UID':<30} Title")
    print("-" * 60)
    for item in items:
        print(f"{item.get('uid', '?'):<30} {item.get('title', '?')}")


def push_dashboard(grafana_url: str, api_key: str, target_uid: str | None = None) -> None:
    with open(DASHBOARD_PATH) as f:
        raw = f.read()

    actual_uid = resolve_prometheus_uid(grafana_url, api_key)
    if actual_uid != PROM_PLACEHOLDER:
        print(f"Datasource UID: {PROM_PLACEHOLDER} → {actual_uid}")
        raw = raw.replace(PROM_PLACEHOLDER, actual_uid)
    else:
        print(f"Datasource UID: {PROM_PLACEHOLDER} (no substitution needed)")

    dashboard = json.loads(raw)
    dashboard["id"] = None
    if target_uid:
        dashboard["uid"] = target_uid

    payload = json.dumps({
        "dashboard": dashboard,
        "overwrite": True,
        "message": "Updated via push_cloud_dashboard.py",
    }).encode()

    req = urllib.request.Request(
        grafana_url.rstrip("/") + "/api/dashboards/db",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    print(f"Done — {grafana_url.rstrip('/')}{result.get('url', '')}")


if __name__ == "__main__":
    load_env(os.path.join(SCRIPT_DIR, ".env"))

    grafana_url = os.environ.get("GRAFANA_CLOUD_URL")
    api_key = os.environ.get("GRAFANA_CLOUD_API_KEY")

    if not grafana_url or not api_key:
        print(
            "Missing environment variables. Add to monitoring/.env:\n"
            "  GRAFANA_CLOUD_URL      e.g. https://chinlablics.grafana.net\n"
            "  GRAFANA_CLOUD_API_KEY  service account token with Editor role",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        if "--list" in sys.argv:
            list_dashboards(grafana_url, api_key)
        else:
            uid = None
            if "--uid" in sys.argv:
                uid = sys.argv[sys.argv.index("--uid") + 1]
            push_dashboard(grafana_url, api_key, uid)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
