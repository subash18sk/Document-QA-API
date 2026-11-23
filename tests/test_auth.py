def test_signup_login_me(client):
    r = client.post("/auth/signup", json={"email": "a@example.com", "password": "secret123"})
    assert r.status_code == 201 and "password_hash" not in r.json()
    token = client.post("/auth/login", data={"username": "a@example.com", "password": "secret123"}).json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == "a@example.com"


def test_duplicate_and_invalid_signup(client):
    client.post("/auth/signup", json={"email": "a@example.com", "password": "secret123"})
    assert client.post("/auth/signup", json={"email": "a@example.com", "password": "secret123"}).status_code == 409
    assert client.post("/auth/signup", json={"email": "nope", "password": "secret123"}).status_code == 422


def test_bad_login_is_generic(client):
    client.post("/auth/signup", json={"email": "a@example.com", "password": "secret123"})
    wrong = client.post("/auth/login", data={"username": "a@example.com", "password": "bad"})
    unknown = client.post("/auth/login", data={"username": "x@example.com", "password": "bad"})
    assert wrong.status_code == unknown.status_code == 401 and wrong.json() == unknown.json()


def test_health_reports_providers_without_secrets(client):
    body = client.get("/health").json()
    assert body == {"status": "ok", "embeddings": "hash-1024", "answerer": "extractive"}
