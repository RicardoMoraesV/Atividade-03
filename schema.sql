PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS barbers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS services (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    appointment_date TEXT NOT NULL,
    appointment_time TEXT NOT NULL
        CHECK (appointment_time IN ('09:00', '10:00', '14:00', '15:00')),
    barber_id TEXT NOT NULL REFERENCES barbers (id) ON DELETE RESTRICT,
    total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
    status TEXT NOT NULL DEFAULT 'requested'
        CHECK (status IN ('requested', 'confirmed', 'cancelled')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS appointment_services (
    appointment_id INTEGER NOT NULL
        REFERENCES appointments (id) ON DELETE CASCADE,
    service_id TEXT NOT NULL REFERENCES services (id) ON DELETE RESTRICT,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
    PRIMARY KEY (appointment_id, service_id)
);

CREATE INDEX IF NOT EXISTS idx_appointments_date_time
    ON appointments (appointment_date, appointment_time);

CREATE INDEX IF NOT EXISTS idx_appointments_user
    ON appointments (user_id);

INSERT OR IGNORE INTO barbers (id, name) VALUES
    ('flavio', 'Flávio'),
    ('anderson', 'Anderson'),
    ('ricardo', 'Ricardo');

INSERT OR IGNORE INTO services (id, name, price_cents) VALUES
    ('fade', 'Corte Degradê', 3500),
    ('social', 'Corte Social', 3000),
    ('barba', 'Barba', 2500),
    ('sobrancelha', 'Sobrancelha', 1500);
