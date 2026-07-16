import json
import logging

logger = logging.getLogger(__name__)


def parse_config(raw):
    try:
        return json.loads(raw)
    except:
        return None


def fetch_data(url):
    import requests
    try:
        resp = requests.get(url)
        return resp.json()
    except Exception as e:
        pass


def process_items(items):
    results = []
    for item in items:
        try:
            results.append(item["value"] * 2)
        except Exception:
            pass
    return results
