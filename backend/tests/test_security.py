from core.security import hash_password, verify_password


def test_hash_is_not_plaintext():
    assert "mypassword" not in hash_password("mypassword")


def test_verify_correct_password():
    assert verify_password("mypassword", hash_password("mypassword")) is True


def test_verify_wrong_password():
    assert verify_password("other", hash_password("mypassword")) is False


def test_same_password_gives_different_hashes():
    assert hash_password("abc12345") != hash_password("abc12345")


def test_verify_malformed_hash_returns_false():
    assert verify_password("x", "not-a-valid-hash") is False
