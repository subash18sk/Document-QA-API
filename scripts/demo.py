"""
End-to-end demo of the Document Q&A API against a running server.

    python scripts/demo.py                       # local server on http://127.0.0.1:8000
    python scripts/demo.py https://your-app.onrender.com

It signs up a throwaway demo user, uploads the sample HR policy PDF, asks questions
(including ones the document can't answer), and shows that another user can't see the document.
"""
import os
import pathlib
import sys
import textwrap
import time
import uuid

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
SAMPLE = pathlib.Path(__file__).resolve().parent.parent / "sample_docs" / "lumenbay-hr-policy.pdf"

QUESTIONS = [
    "How many paid leaves do I get?",
    "What is the notice period during probation?",
    "How much health insurance cover do employees have?",
    "Is internet reimbursed?",
    "What is the company's stock price?",      # not in the document -> honest refusal
    "Who won the cricket world cup?",          # not in the document -> honest refusal
]


def step(title):
    print(f"\n\033[1m== {title} ==\033[0m")


def wait_for_server(client):
    for _ in range(30):
        try:
            return client.get("/health").json()
        except httpx.HTTPError:
            time.sleep(1)
    sys.exit(f"Server not reachable at {BASE}. Start it first: uvicorn app.main:app")


def new_user(client):
    email, password = f"demo-{uuid.uuid4().hex[:8]}@example.com", "demo-password"
    client.post("/auth/signup", json={"email": email, "password": password}).raise_for_status()
    token = client.post("/auth/login", data={"username": email, "password": password}).json()["access_token"]
    return email, {"Authorization": f"Bearer {token}"}


def main():
    if os.name == "nt":
        os.system("")  # enables colour codes in the classic Windows console
    with httpx.Client(base_url=BASE, timeout=60) as client:
        step("1. Health check")
        health = wait_for_server(client)
        print(f"Server is up. Embeddings: {health['embeddings']} | Answers: {health['answerer']}")

        step("2. Sign up and log in")
        email, auth = new_user(client)
        print(f"Created {email} and received a JWT token.")

        step("3. Upload the sample PDF")
        with SAMPLE.open("rb") as f:
            r = client.post("/documents", headers=auth, files={"file": (SAMPLE.name, f, "application/pdf")})
        r.raise_for_status()
        doc = r.json()
        print(f"Indexed '{doc['filename']}': {doc['page_count']} pages -> {doc['chunk_count']} searchable chunks.")

        step("4. Ask questions")
        for q in QUESTIONS:
            a = client.post(f"/documents/{doc['id']}/ask", headers=auth, json={"question": q}).json()
            mark = "\033[32mFOUND    \033[0m" if a["found"] else "\033[33mNOT FOUND\033[0m"
            print(f"\nQ: {q}\n{mark} " + textwrap.fill(a["answer"], 90, subsequent_indent=" " * 10))
            if a["sources"]:
                s = a["sources"][0]
                print(f"          source: page {s['page']}, similarity {s['score']:.2f}")

        step("5. Privacy check: a second user tries to read the document")
        _, other = new_user(client)
        status = client.get(f"/documents/{doc['id']}", headers=other).status_code
        print(f"Second user gets HTTP {status} (expected 404: they can't even tell it exists).")

        step("6. Clean up")
        client.delete(f"/documents/{doc['id']}", headers=auth).raise_for_status()
        print("Deleted the document and all of its stored vectors.")
        print(f"\nTry it yourself in the browser: {BASE}/docs\n")


if __name__ == "__main__":
    main()
