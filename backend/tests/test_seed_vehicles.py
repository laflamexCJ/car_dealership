from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from sqlalchemy import select

from test_api import auth, client, vehicle
from seed_vehicles import SAMPLE_VEHICLES, seed_vehicles


def test_seed_preserves_records_and_is_idempotent(client):
    from main import User, Vehicle

    headers = auth(client)
    original = vehicle(client, headers)
    engine = client.app.state.engine
    with engine.connect() as connection:
        users_before = connection.execute(select(User.__table__)).all()
    assert len(SAMPLE_VEHICLES) == 20
    assert seed_vehicles(engine) == 20
    assert seed_vehicles(engine) == 0
    inventory = client.get('/api/vehicles', headers=headers).json()
    assert len(inventory) == 21
    assert next(row for row in inventory if row['id'] == original['id']) == original
    with engine.connect() as connection:
        assert connection.execute(select(User.__table__)).all() == users_before
    # A purchase must not be undone by re-running the seed.
    sample = next(row for row in inventory if row['model'] == 'Corolla LE')
    assert client.post(f'/api/vehicles/{sample["id"]}/purchase', headers=headers,
                       json={'quantity': 1}).status_code == 200
    assert seed_vehicles(engine) == 0
    with engine.connect() as connection:
        assert connection.scalar(select(Vehicle.quantity).where(Vehicle.id == sample['id'])) == 7
    response = client.get('/api/vehicles/search', headers=headers,
                          params={'category': 'SUV', 'min_price': 30000, 'max_price': 42000})
    assert response.status_code == 200
    assert len(response.json()) == 4
    assert all(row['category'] == 'SUV' and Decimal('30000') <= Decimal(row['price']) <= Decimal('42000') for row in response.json())
    assert len(client.get('/api/vehicles/search', headers=headers, params={'q': 'Hybrid'}).json()) == 2
    assert client.get('/api/vehicles').status_code == 401


def test_concurrent_seed_and_existing_match(client):
    headers = auth(client)
    existing = client.post('/api/vehicles', headers=headers, json={
        'make': 'Toyota', 'model': 'Corolla LE', 'category': 'Sedan',
        'price': '10000.00', 'quantity': 1,
    }).json()
    engine = client.app.state.engine
    with ThreadPoolExecutor(max_workers=2) as pool:
        counts = list(pool.map(lambda _: seed_vehicles(engine), range(2)))
    assert sorted(counts) == [0, 19]
    rows = client.get('/api/vehicles', headers=headers).json()
    assert len(rows) == 20
    assert next(row for row in rows if row['id'] == existing['id']) == existing
