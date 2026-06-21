"""OpenAPI docs are grouped under named tags (#34)."""


def test_openapi_has_grouped_tags(client):
    schema = client.get("/openapi.json").json()
    tag_names = {t["name"] for t in schema.get("tags", [])}
    assert {"System", "Analysis", "History", "Analytics", "Reports"} <= tag_names
    # every documented operation carries a tag
    used = {
        t
        for p in schema["paths"].values()
        for op in p.values()
        if isinstance(op, dict)
        for t in op.get("tags", [])
    }
    assert "Analysis" in used and "Reports" in used
