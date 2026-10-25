"""Load 20 demo listings without replacing existing inventory or users."""
from sqlalchemy import select

# USD demonstration prices, not live dealer quotes. Only existing schema fields.
SAMPLE_VEHICLES = (
    ('Toyota', 'Corolla LE', 'Sedan', '22950.00', 8),
    ('Toyota', 'Camry Hybrid LE', 'Sedan', '28900.00', 4),
    ('Toyota', 'RAV4 XLE', 'SUV', '31950.00', 6),
    ('Honda', 'Civic Sport', 'Sedan', '25900.00', 7),
    ('Honda', 'CR-V Hybrid Sport', 'SUV', '34950.00', 3),
    ('Mazda', 'Mazda3 Select', 'Hatchback', '24900.00', 5),
    ('Mazda', 'MX-5 Miata Sport', 'Convertible', '29950.00', 2),
    ('Ford', 'F-150 XLT', 'Truck', '45900.00', 4),
    ('Ford', 'Mustang EcoBoost', 'Coupe', '32900.00', 2),
    ('Ford', 'Mustang Mach-E Select', 'SUV', '39900.00', 3),
    ('Chevrolet', 'Silverado 1500 LT', 'Truck', '43950.00', 5),
    ('Hyundai', 'Elantra SE', 'Sedan', '21500.00', 9),
    ('Hyundai', 'IONIQ 5 SE', 'SUV', '41900.00', 2),
    ('Kia', 'Soul LX', 'Hatchback', '19950.00', 6),
    ('Subaru', 'Outback Premium', 'Wagon', '32950.00', 4),
    ('Volkswagen', 'Golf GTI S', 'Hatchback', '31900.00', 0),
    ('Tesla', 'Model 3 Long Range', 'Sedan', '42900.00', 3),
    ('BMW', '330i', 'Sedan', '44950.00', 2),
    ('Mercedes-Benz', 'GLC 300', 'SUV', '48900.00', 1),
    ('Porsche', '718 Cayman', 'Coupe', '68900.00', 0),
)


def seed_vehicles(engine):
    from main import Base, Vehicle, VehicleCreate

    # Validate everything before opening the write transaction.
    samples = [VehicleCreate(make=make, model=model, category=category,
                             price=price, quantity=quantity).model_dump()
               for make, model, category, price, quantity in SAMPLE_VEHICLES]
    if engine.dialect.name != 'sqlite':
        raise ValueError('This seed command supports the application SQLite database only.')
    inserted = 0
    with engine.connect() as connection:
        # Serialize concurrent seed runs without adding a constraint or changing schema.
        connection.exec_driver_sql('BEGIN IMMEDIATE')
        try:
            # Importing the app does not run its lifespan; create only missing tables.
            Base.metadata.create_all(connection)
            existing = {tuple(row) for row in connection.execute(select(Vehicle.make, Vehicle.model, Vehicle.category))}
            for sample in samples:
                key = (sample['make'], sample['model'], sample['category'])
                if key not in existing:
                    connection.execute(Vehicle.__table__.insert().values(**sample))
                    existing.add(key)
                    inserted += 1
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return inserted


if __name__ == '__main__':
    from main import app

    # Use the same engine/configuration as the API. Run from backend/ just like the API.
    count = seed_vehicles(app.state.engine)
    print(f'Added {count} sample vehicles; skipped {len(SAMPLE_VEHICLES) - count} existing matches.')
