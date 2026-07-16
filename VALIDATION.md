# MVP Validation Report

**Project:** Continuous Discovery Beacon  
**Version:** 0.1.0  
**Validation date:** 2026-07-16

## Automated tests

Command:

```bash
pytest
```

Result:

```text
.....                                                                    [100%]
5 passed in 0.30s
```

Covered behaviors:

1. Health endpoint responds successfully.
2. Write endpoints reject missing Bearer tokens when a token is configured.
3. Site and event creation complete successfully.
4. URL canonicalization forces HTTPS, removes tracking parameters and normalizes trailing slashes.
5. Cross-host event URLs are rejected.
6. Identical content events are deduplicated.
7. Manual dispatch records per-channel outcomes.
8. Missing IndexNow key is represented as `skipped`, never as a false success.
9. Database-backed Sitemap, RSS, JSONL changes and discovery documents reflect created events.

## Packaging validation

Commands:

```bash
python -m compileall -q app scripts
python -m pip install --no-deps -e .
```

Result:

- Python modules compiled successfully.
- Editable package wheel built and installed successfully.

## Known MVP limitations

- BackgroundTasks is suitable for the MVP but is not a durable distributed queue.
- SQLite is suitable for a single instance; production horizontal scaling should use PostgreSQL.
- `content_hash` is supplied by a deployment pipeline or CMS; the MVP does not fetch pages itself.
- Git file paths require a site-specific mapping rule before they can become public absolute URLs.
- Crawler telemetry, WebSub and subscriber Webhooks are deferred to later versions.
