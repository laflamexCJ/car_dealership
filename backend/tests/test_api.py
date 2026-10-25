import secrets
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{tmp_path / "test.db"}')
    monkeypatch.setenv('JWT_SECRET_KEY', secrets.token_urlsafe(48))
    from main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c
    app.state.engine.dispose()

def register(c, email='user@example.com'):
    return c.post('/api/auth/register', json={'email': email, 'password': 'test-password-123'})

def auth(c, email='user@example.com', admin=False):
    register(c, email)
    if admin:
        with c.app.state.engine.begin() as conn:
            conn.execute(text('UPDATE users SET role=:role WHERE email=:email'), {'role': 'admin', 'email': email})
    r = c.post('/api/auth/login', json={'email': email, 'password': 'test-password-123'})
    assert r.status_code == 200
    return {'Authorization': f'Bearer {r.json()["access_token"]}'}

def vehicle(c, h, quantity=2):
    r = c.post('/api/vehicles', headers=h, json={'make': 'Toyota', 'model': 'Corolla', 'category': 'Sedan', 'price': 25000.50, 'quantity': quantity})
    assert r.status_code == 201, r.text
    return r.json()

def test_registration_duplicate(client):
    r = register(client, 'User@Example.com')
    assert r.status_code == 201 and r.json()['role'] == 'user'
    assert 'password' not in r.json() and 'password_hash' not in r.json()
    assert register(client).status_code == 409

def test_login(client):
    register(client)
    r = client.post('/api/auth/login', json={'email': 'user@example.com', 'password': 'test-password-123'})
    assert r.status_code == 200 and r.json()['access_token']
    for email, password in [('user@example.com', 'wrong'), ('missing@example.com', 'test-password-123')]:
        assert client.post('/api/auth/login', json={'email': email, 'password': password}).status_code == 401

def test_create_list(client):
    h = auth(client)
    item = vehicle(client, h)
    r = client.get('/api/vehicles', headers=h)
    assert r.status_code == 200 and r.json() == [item]

def test_purchase_stock(client):
    h = auth(client)
    item = vehicle(client, h)
    url = f'/api/vehicles/{item["id"]}/purchase'
    assert client.post(url, headers=h, json={'quantity': 3}).status_code == 409
    r = client.post(url, headers=h, json={'quantity': 2})
    assert r.status_code == 200 and r.json()['quantity'] == 0
    assert client.post(url, headers=h, json={'quantity': 1}).status_code == 409
    assert client.get('/api/vehicles', headers=h).json()[0]['quantity'] == 0

def test_admin_only(client):
    h = auth(client)
    admin = auth(client, 'admin@example.com', True)
    item = vehicle(client, h)
    url = f'/api/vehicles/{item["id"]}'
    assert client.post(url + '/restock', headers=h, json={'quantity': 3}).status_code == 403
    assert client.delete(url, headers=h).status_code == 403
    r = client.post(url + '/restock', headers=admin, json={'quantity': 3})
    assert r.status_code == 200 and r.json()['quantity'] == 5
    assert client.delete(url, headers=admin).status_code == 204
    assert client.get('/api/vehicles', headers=admin).json() == []

@pytest.mark.parametrize('method,path', [('get', '/api/vehicles'), ('get', '/api/vehicles/search'), ('post', '/api/vehicles'), ('put', '/api/vehicles/1'), ('delete', '/api/vehicles/1'), ('post', '/api/vehicles/1/purchase'), ('post', '/api/vehicles/1/restock')])
def test_unauthenticated(client, method, path):
    assert getattr(client, method)(path).status_code == 401

@pytest.mark.parametrize('quantity', [0, -1, 1.5, True])
def test_invalid_quantities(client, quantity):
    h = auth(client, admin=True)
    item = vehicle(client, h)
    for action in ['purchase', 'restock']:
        assert client.post(f'/api/vehicles/{item["id"]}/{action}', headers=h, json={'quantity': quantity}).status_code == 422
    assert client.get('/api/vehicles', headers=h).json()[0]['quantity'] == 2

def test_search_update_missing(client):
    h = auth(client)
    item = vehicle(client, h)
    assert len(client.get('/api/vehicles/search', headers=h, params={'make': 'toy', 'category': 'sedan', 'min_price': 20000, 'max_price': 30000}).json()) == 1
    assert client.get('/api/vehicles/search', headers=h, params={'q': 'truck'}).json() == []
    r = client.put(f'/api/vehicles/{item["id"]}', headers=h, json={'model': 'Camry', 'price': 30000})
    assert r.status_code == 200 and r.json()['model'] == 'Camry'
    assert client.put(f'/api/vehicles/{item["id"]}', headers=h, json={'quantity': 100}).status_code == 422
    assert client.put('/api/vehicles/999', headers=h, json={'model': 'Missing'}).status_code == 404

def test_validation_and_escalation(client):
    assert client.post('/api/auth/register', json={'email': 'bad', 'password': 'short'}).status_code == 422
    assert client.post('/api/auth/register', json={'email': 'admin@example.com', 'password': 'test-password-123', 'role': 'admin'}).status_code == 422
    h = auth(client)
    assert client.post('/api/vehicles', headers=h, json={'make': ' ', 'model': 'X', 'category': 'SUV', 'price': -1, 'quantity': -1}).status_code == 422
    assert client.get('/api/vehicles', headers={'Authorization': 'Bearer invalid'}).status_code == 401


def test_concurrent_purchase(client):
    from concurrent.futures import ThreadPoolExecutor
    h = auth(client)
    item = vehicle(client, h, quantity=1)
    def buy(_):
        return client.post(f'/api/vehicles/{item["id"]}/purchase', headers=h, json={'quantity': 1}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(buy, range(2))) == [200, 409]
    assert client.get('/api/vehicles', headers=h).json()[0]['quantity'] == 0


def test_password_storage_and_expired_token(client, monkeypatch):
    import os
    import jwt
    from datetime import datetime, timedelta, timezone
    from pwdlib import PasswordHash
    register(client)
    with client.app.state.engine.connect() as conn:
        stored = conn.execute(text('SELECT id, password_hash FROM users')).one()
    assert stored.password_hash != 'test-password-123'
    assert PasswordHash.recommended().verify('test-password-123', stored.password_hash)
    token = jwt.encode({'sub': str(stored.id), 'exp': datetime.now(timezone.utc) - timedelta(minutes=1)}, os.environ['JWT_SECRET_KEY'], algorithm='HS256')
    assert client.get('/api/vehicles', headers={'Authorization': f'Bearer {token}'}).status_code == 401


def test_missing_stock_and_overflow(client):
    h = auth(client, admin=True)
    for action in ['purchase', 'restock']:
        assert client.post(f'/api/vehicles/999/{action}', headers=h, json={'quantity': 1}).status_code == 404
    item = vehicle(client, h, quantity=2_147_483_647)
    assert client.post(f'/api/vehicles/{item["id"]}/restock', headers=h, json={'quantity': 1}).status_code == 409
    assert client.get('/api/vehicles', headers=h).json()[0]['quantity'] == 2_147_483_647
