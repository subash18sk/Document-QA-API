def test_web_app_is_served_at_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "Ask the Document" in r.text


def test_sample_document_is_downloadable(client):
    r = client.get("/sample-document")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
