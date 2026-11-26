from datetime import datetime
from decimal import Decimal
from urllib.parse import parse_qsl, urlsplit

import pytest
from fastapi import HTTPException

from integrations import google_oauth as g
from integrations import vnpay as v

CFG = {"tmn": "TMN1", "secret": "SECRET", "url": "https://sandbox.example/pay", "return_url": "http://x/return", "front": "/f"}


def test_vnpay_url_signature_roundtrip():
    url = v.build_url(7, Decimal("250000"), "1.2.3.4", CFG, datetime(2026, 11, 25, 8, 0, 0))
    params = dict(parse_qsl(urlsplit(url).query))
    assert params["vnp_Amount"] == "25000000" and params["vnp_TxnRef"].startswith("7-")
    assert v.verify(params, "SECRET")
    params["vnp_Amount"] = "100"
    assert not v.verify(params, "SECRET")
    assert not v.verify({"vnp_Amount": "1"}, "SECRET")


def test_settle_rejects_bad_signature(monkeypatch):
    monkeypatch.setattr(v, "_cfg", lambda: CFG)
    res = v.settle({"vnp_TxnRef": "7-1", "vnp_Amount": "100", "vnp_SecureHash": "bad"})
    assert res["ok"] is False and res["code"] == "97"


def test_settle_failed_payment_not_recorded(monkeypatch):
    monkeypatch.setattr(v, "_cfg", lambda: CFG)
    p = {"vnp_TxnRef": "7-1", "vnp_Amount": "100", "vnp_ResponseCode": "24"}
    p["vnp_SecureHash"] = v.sign(p, "SECRET")
    assert v.settle(p)["ok"] is False


def test_google_claims():
    ok = {"aud": "cid", "iss": "accounts.google.com", "email": "A@B.com", "email_verified": "true", "name": "An"}
    assert g.check_claims(ok, ["cid"]) == {"email": "a@b.com", "name": "An"}
    for bad in ({**ok, "aud": "other"}, {**ok, "iss": "evil"}, {**ok, "email_verified": "false"}):
        with pytest.raises(HTTPException) as e:
            g.check_claims(bad, ["cid"])
        assert e.value.status_code == 401
    with pytest.raises(HTTPException) as e:
        g.check_claims(ok, [])
    assert e.value.status_code == 503
