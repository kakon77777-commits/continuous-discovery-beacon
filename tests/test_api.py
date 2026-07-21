from __future__ import annotations


def create_site(client, auth_headers, site_id="logic_evemisslab", base_url="https://logic.evemisslab.com"):
    response = client.post(
        "/api/v1/sites",
        headers=auth_headers,
        json={
            "id": site_id,
            "name": "EVEMISSLAB Logic",
            "base_url": base_url,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert "submit_token" in data
    return data


def submit_headers(site):
    return {"Authorization": f"Bearer {site['submit_token']}"}


def test_health(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_write_requires_token(client):
    response = client.post(
        "/api/v1/sites",
        json={"id": "site_one", "name": "One", "base_url": "https://example.com"},
    )
    assert response.status_code == 401


def test_create_dispatch_and_public_outputs(client, auth_headers):
    site = create_site(client, auth_headers)
    payload = {
        "site_id": "logic_evemisslab",
        "url": "http://logic.evemisslab.com/paper/demo/?utm_source=test",
        "event_type": "created",
        "content_hash": "sha256:abc",
        "title": "Demo Paper",
        "summary": "A discovery beacon test.",
        "auto_dispatch": False,
    }
    response = client.post("/api/v1/events", headers=submit_headers(site), json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["canonical_url"] == "https://logic.evemisslab.com/paper/demo"
    event_id = data["id"]

    dispatch = client.post(f"/api/v1/events/{event_id}/dispatch", headers=auth_headers)
    assert dispatch.status_code == 200, dispatch.text
    dispatch_data = dispatch.json()
    assert dispatch_data["event_status"] == "completed"
    statuses = {item["channel"]: item["status"] for item in dispatch_data["deliveries"]}
    assert statuses["indexnow"] == "skipped"
    assert statuses["sitemap"] == "success"
    assert statuses["rss"] == "success"
    assert statuses["changes"] == "success"

    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert "https://logic.evemisslab.com/paper/demo" in sitemap.text

    feed = client.get("/feed.xml")
    assert feed.status_code == 200
    assert "Demo Paper" in feed.text

    changes = client.get("/changes.jsonl")
    assert changes.status_code == 200
    assert event_id in changes.text

    discovery = client.get("/.well-known/discovery.json")
    assert discovery.status_code == 200
    assert discovery.json()["sites"][0]["id"] == "logic_evemisslab"


def test_event_deduplication(client, auth_headers):
    site = create_site(client, auth_headers)
    payload = {
        "site_id": "logic_evemisslab",
        "url": "https://logic.evemisslab.com/paper/demo",
        "event_type": "updated",
        "content_hash": "sha256:same",
        "auto_dispatch": False,
    }
    first = client.post("/api/v1/events", headers=submit_headers(site), json=payload)
    second = client.post("/api/v1/events", headers=submit_headers(site), json=payload)
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert first.json()["id"] == second.json()["id"]


def test_rejects_cross_host_url(client, auth_headers):
    site = create_site(client, auth_headers)
    response = client.post(
        "/api/v1/events",
        headers=submit_headers(site),
        json={
            "site_id": "logic_evemisslab",
            "url": "https://evil.example.net/page",
            "event_type": "created",
            "content_hash": "sha256:x",
            "auto_dispatch": False,
        },
    )
    assert response.status_code == 422


def test_event_submission_requires_site_token(client, auth_headers):
    create_site(client, auth_headers)
    response = client.post(
        "/api/v1/events",
        json={
            "site_id": "logic_evemisslab",
            "url": "https://logic.evemisslab.com/paper/demo",
            "event_type": "created",
            "content_hash": "sha256:x",
            "auto_dispatch": False,
        },
    )
    assert response.status_code == 401


def test_site_token_cannot_submit_for_another_site(client, auth_headers):
    site_a = create_site(client, auth_headers, site_id="site_a", base_url="https://a.example.com")
    create_site(client, auth_headers, site_id="site_b", base_url="https://b.example.com")

    response = client.post(
        "/api/v1/events",
        headers=submit_headers(site_a),
        json={
            "site_id": "site_b",
            "url": "https://b.example.com/page",
            "event_type": "created",
            "content_hash": "sha256:x",
            "auto_dispatch": False,
        },
    )
    assert response.status_code == 403


def test_admin_token_alone_cannot_submit_events(client, auth_headers):
    create_site(client, auth_headers)
    response = client.post(
        "/api/v1/events",
        headers=auth_headers,
        json={
            "site_id": "logic_evemisslab",
            "url": "https://logic.evemisslab.com/paper/demo",
            "event_type": "created",
            "content_hash": "sha256:x",
            "auto_dispatch": False,
        },
    )
    assert response.status_code == 403
