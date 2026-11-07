from app.security import hash_password, verify_password, create_access_token

def test_password_hash_and_verify():
    hashed=hash_password("a-strong-test-password")
    assert hashed != "a-strong-test-password"
    assert verify_password("a-strong-test-password",hashed)
    assert not verify_password("wrong-password",hashed)

def test_token_creation():
    token=create_access_token("42")
    assert isinstance(token,str) and len(token)>20
