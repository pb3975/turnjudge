"""One test per redaction rule plus a 50/50 corpus of known secrets and false-positive candidates."""
import pytest

from jev_review.redact import (ENTROPY_THRESHOLD, cap, deny_reason, redact_diff, scrub_secrets, shannon_entropy,
                               trim_identity)

# ---- deny list -------------------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    ".env", ".env.local", "config/.env.production", "prod.env", "server.pem", "keys/host.key", "id_rsa", "id_ed25519.pub",
    "certs/client.p12", "app/secrets.yaml", "aws_credentials", "credentials.json", "bundle.min.js", "style.min.css",
    "package-lock.json", "yarn.lock", "uv.lock", "Cargo.lock", "go.sum", "poetry.lock", "pnpm-lock.yaml",
    "dist/app.js", "node_modules/x/index.js", "proto/api.pb.go", "gen/schema_pb2.py", "logo.png", "font.woff2",
])
def test_denied(path):
    assert deny_reason(path) is not None, path


@pytest.mark.parametrize("path", [
    "src/app.py", "internal/cli/agent.go", "README.md", "environment.ts", "keyboard.py", "lockfile_parser.py",
    "src/secrets_ui/panel.tsx".replace("secrets_ui", "settings_ui"), "docs/credits.md", "envelope.go",
])
def test_allowed(path):
    assert deny_reason(path) is None, path


def test_extra_deny_paths():
    assert deny_reason("infra/secrets/x.yaml", ["infra/secrets/**"]) == "deny-path:infra/secrets/**"
    assert deny_reason("infra/other/x.yaml", ["infra/secrets/**"]) is None


# ---- secret patterns: one test per kind ------------------------------------------------------

@pytest.mark.parametrize("kind,text", [
    ("aws_access_key", "aws_key = 'AKIAIOSFODNN7EXAMPLE'"),
    ("private_key", "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\n-----END RSA PRIVATE KEY-----"),
    ("github_token", "token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"),
    ("gitlab_token", "glpat-abcdefghij1234567890"),
    ("slack_token", "xoxb-123456789012-abcdefghijkl"),
    ("slack_webhook", "https://hooks.slack.com/services/T000/B000/XXXXXXXX"),
    ("stripe_key", "sk_live_abcdefghijklmnop123456"),
    ("openai_style_key", "OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz0123"),
    ("google_api_key", "AIzaSyA1234567890abcdefghijklmnopqrstuv"),
    ("sendgrid_key", "SG.abcdefghijklmnopq.abcdefghijklmnopqrstuvwxyz"),
    ("npm_token", "npm_abcdefghijklmnopqrstuvwxyz0123456789"),
    ("jwt", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"),
    ("bearer", "Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345"),
    ("basic_auth_header", "Authorization: Basic dXNlcjpwYXNzd29yZA=="),
    ("url_userinfo", "postgres://admin:hunter22@db.internal:5432/app"),
    ("assigned_secret", 'password = "correct-horse-battery"'),
    ("apikey_prefix", "apikey_abcdefghijklmnop1234"),
    ("high_entropy", "SESSION_SECRET=q9Zr2vL8kPwX4nTb7YsC1mHf6GdJ3eKu"),
])
def test_pattern(kind, text):
    out, counts = scrub_secrets(text)
    assert kind in counts, (kind, out, counts)
    assert f"<REDACTED:{kind}>" in out


def test_bearer_keeps_header_name():
    out, _ = scrub_secrets("Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345")
    assert out.startswith("Authorization: Bearer <REDACTED")


def test_url_userinfo_keeps_host():
    out, _ = scrub_secrets("https://user:s3cretpassw0rd@example.com/path")
    assert out == "https://<REDACTED:url_userinfo>@example.com/path"


def test_custom_pattern():
    out, counts = scrub_secrets("internal-token-XYZ", ["internal-token-[A-Z]+"])
    assert counts.get("custom") == 1 and "XYZ" not in out


def test_entropy():
    assert shannon_entropy("aaaaaaaa") == 0
    assert shannon_entropy("q9Zr2vL8kPwX4nTb7YsC1mHf6GdJ3eKu") > ENTROPY_THRESHOLD


# ---- corpus: 50 secrets that must be redacted, 50 look-alikes that must survive ----------------

SECRETS = [
    "AKIAIOSFODNN7EXAMPLE", "ASIAJEXAMPLEEXAMPLE1", "AKIAABCDEFGHIJKLMNOP",
    "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8", "gho_" + "abcdefghijklmnopqrstuvwxyz0123456789",
    "github_pat_11ABCDEFG0abcdefghijklmnopqrstuvwxyz",
    "glpat-AbCdEfGhIjKlMnOpQrSt", "xoxp-1234567890-1234567890-abcdefghijkl", "xoxa-2-abcdefghijklmnopqrstuv",
    "https://hooks.slack.com/services/T0AAA/B0BBB/abcdefghijklmnopqrstuvwx",
    "sk_test_4eC39HqLyjWDarjtT1zdp7dc", "rk_live_abcdefghijklmnopqrstuvwx", "pk_live_abcdefghijklmnopqrstuvwx",
    "sk-abcdefghijklmnopqrstuvwxyz0123456789", "sk-ant-api03-abcdefghijklmnopqrstuvwxyz", "sk-or-v1-abcdefghijklmnopqrstuvwxyz",
    "AIzaSyDaGmWKa4JsXZ-HjGw7ISLn_3namBGewQe", "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",
    "npm_1234567890abcdefghijklmnopqrstuvwxyz",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
    "Authorization: Bearer ya29.a0AfH6SMBx1234567890abcdefghijklmnop", "authorization: bearer abcdefghijklmnopqrstuvwxyzABCDEF",
    "Authorization: Basic YWRtaW46c3VwZXJzZWNyZXQ=", "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAA\n-----END OPENSSH PRIVATE KEY-----",
    "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEIB\n-----END EC PRIVATE KEY-----",
    "mysql://root:P%40ssw0rd123@db:3306/x", "redis://:hunter2hunter2@cache:6379", "amqp://guest:guestpass@mq/",
    "password = 'Tr0ub4dor&3xyz'", 'PASSWORD: "winter2024!!"', "client_secret = 'a1b2c3d4e5f6g7h8i9j0'",
    "api_key: 'ZmFrZWtleWZha2VrZXlmYWtla2V5'", "AUTH_TOKEN=\"t0k3n-t0k3n-t0k3n-t0k3n\"", "private_key = 'MIIEvQIBADANBg'",
    "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "apikey_ABCDEFGHIJKLMNOPQRSTUVWX", "api_key_0123456789abcdefghij",
    "SECRET=8fJq2LmZx9Kp3WvRt7YbN4cH6sDgA1eU", "-H 'X-Api-Key: 9d8f7a6s5d4f3g2h1j0kL9M8N7B6V5C4X3Z2'",
    "token = \"d9f8a7s6d5f4g3h2j1k0l9m8n7b6v5c4\"", "pypi-AgEIcHlwaS5vcmcCJDAwMDAwMDAwLTAwMDAtMDAwMC0wMDAwLTAwMDAwMDAwMDAwMA",
    "xoxs-abcdefghij-klmnopqrstu", "xoxr-abcdefghij-klmnopqrstu", "ghs_abcdefghijklmnopqrstuvwxyz0123456789",
    "ghu_abcdefghijklmnopqrstuvwxyz0123456789", "ghr_abcdefghijklmnopqrstuvwxyz0123456789",
    "https://x.com/?k=1 Authorization=Bearer Zm9vYmFyYmF6cXV4cXV1eA==abc", "passwd: \"n0tS0S3cr3tButL0ng\"",
    "access_key = \"AKIAZZZZZZZZZZZZZZZZ\"", "APP_KEY=base64:Qk9PVEFQUEtFWVNFQ1JFVDEyMzQ1Njc4OTA=",
]
LOOKALIKES = [
    "def main():\n    return 1", "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "commit 2f4369b806c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5", "md5 = 'd41d8cd98f00b204e9800998ecf8427e'",
    "password = os.environ['DB_PASSWORD']", "api_key = get_secret('api')", "token = request.headers.get('X-Token')",
    "AUTHORIZATION_HEADER = 'Authorization'", "Authorization: Bearer <token>", "Authorization: Bearer ${TOKEN}",
    "password: '{{ vault_db_password }}'", "PASSWORD=changeme", "api_key: your-api-key-here", "token = 'example-token'",
    "secret: REDACTED", "https://example.com/path?query=1", "https://github.com/anthropics/claude-code",
    "postgres://localhost:5432/app", "user@example.com", "import os, sys, json",
    "const MAX_RETRIES = 3", "if err != nil { return fmt.Errorf(\"x: %w\", err) }", "x = 'abcdefghijklmnopqrstuvwxyz'",
    "hello world hello world hello world", "version = '1.2.3'", "AKIA is the prefix for AWS access keys",
    "sk- is the OpenAI prefix", "The bearer of this ticket", "id = 'user_1234567890'", "uuid = '550e8400-e29b-41d4-a716-446655440000'",
    "#!/usr/bin/env bash\nset -euo pipefail", "return {'status': 'ok', 'items': []}", "func (p Profile) validate() error {",
    "log.Info('starting', 'port', 8080)", "const url = new URL(event.url)", "expected = 'The quick brown fox jumps'",
    "# TODO: rotate keys quarterly", "key = 'behavior_added'", "criteria={'true': 'Explicitly time-sensitive'}",
    "path = '/usr/local/bin/python3'", "SELECT id, name FROM users WHERE id = $1", "docker run -d --name app -p 8080:80 image",
    "0123456789012345678901234567890123456789", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "name = 'internal/runtime/firecracker/firecracker.go'", "message = 'session metadata contains credential-shaped material'",
    "regexp.MustCompile(`^[A-Za-z0-9/+=]{40}$`)", "xoxo, the release notes", "pk = primary_key(table)", "ghp = 'gigahertz per'",
]


def test_corpus_sizes():
    assert len(SECRETS) >= 50 and len(LOOKALIKES) >= 50


@pytest.mark.parametrize("s", SECRETS)
def test_corpus_secret_redacted(s):
    out, counts = scrub_secrets(s)
    assert counts, f"not redacted: {s!r} -> {out!r}"
    # the secret material itself must be gone; the longest run of secret-looking chars is absent
    import re
    runs = sorted(re.findall(r"[A-Za-z0-9+/=_.\-]{16,}", s), key=len, reverse=True)
    if runs:
        assert runs[0] not in out, f"leak: {runs[0]!r} in {out!r}"


@pytest.mark.parametrize("s", LOOKALIKES)
def test_corpus_lookalike_survives(s):
    out, counts = scrub_secrets(s)
    assert out == s, f"false positive: {s!r} -> {out!r} ({counts})"


# ---- identity and caps -----------------------------------------------------------------------

def test_trim_identity_home_and_email(monkeypatch):
    import os
    home = os.path.expanduser("~")
    out = trim_identity(f"path {home}/Work/x and mail will@example.org", emails=["will@example.org"])
    assert home not in out and "will@example.org" not in out and "~/Work/x" in out


def test_cap_truncates_on_line_boundary():
    text = "\n".join(f"line {i} " + "x" * 50 for i in range(100))
    out, truncated = cap(text, 1000, "diff")
    assert truncated and out.endswith("<TRUNCATED: diff exceeded 1000 bytes>") and len(out.encode()) < 1100


def test_redact_diff_withheld_and_counts():
    r = redact_diff(".env", "+SECRET=x", per_file_bytes=100)
    assert r.withheld_reason and r.text == ""
    r = redact_diff("app.py", "+token = 'AKIAIOSFODNN7EXAMPLE'\n", per_file_bytes=100)
    assert "<REDACTED:aws_access_key>" in r.text and r.counts["aws_access_key"] == 1
