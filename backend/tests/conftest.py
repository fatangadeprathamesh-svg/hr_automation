import pytest
from datetime import date
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

import sys
import os

backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.database import Base, get_db
from app.models.hr import Employee
from app.main import app

TEST_DB_URL = "sqlite:///:memory:"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    emp1 = Employee(
        employee_id="EMP001",
        organization_id="ORG_DEMO_01",
        email="alice@example.com",
        full_name="Alice Employee",
        manager_id="MGR001",
        timezone="America/New_York",
        hire_date=date(2025, 1, 15),
        is_active=True,
    )
    mgr1 = Employee(
        employee_id="MGR001",
        organization_id="ORG_DEMO_01",
        email="bob.manager@example.com",
        full_name="Bob Manager",
        manager_id=None,
        timezone="America/New_York",
        hire_date=date(2024, 3, 1),
        is_active=True,
    )
    hr1 = Employee(
        employee_id="HR001",
        organization_id="ORG_DEMO_01",
        email="carol.hr@example.com",
        full_name="Carol HR Admin",
        manager_id=None,
        timezone="America/New_York",
        hire_date=date(2023, 6, 1),
        is_active=True,
    )
    ic1 = Employee(
        employee_id="IC001",
        organization_id="ORG_DEMO_01",
        email="irene.ic@example.com",
        full_name="Irene IC Member",
        manager_id=None,
        timezone="Internal Committee",
        hire_date=date(2023, 1, 1),
        is_active=True,
    )
    db.add_all([mgr1, emp1, hr1, ic1])
    db.commit()
    from app.seed import seed_user_accounts
    seed_user_accounts(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    connection = engine.connect()
    trans = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Use nested savepoints so session.commit() inside service/tests works seamlessly
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def end_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    session.close()
    trans.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
