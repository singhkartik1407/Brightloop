
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import Base, User, UserRole, Customer


# --------------------------------
# ISOLATED TEST DATABASE
# --------------------------------

@pytest.fixture
def test_engine():

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# --------------------------------
# TEST DATABASE SESSION
# --------------------------------

@pytest.fixture
def db_session(test_engine):

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False
    )

    with TestingSessionLocal() as session:
        yield session


# --------------------------------
# DEFAULT ADMIN TEST USER
# --------------------------------

@pytest.fixture
def test_user(db_session):

    user = User(
        email="admin@example.com",
        password_hash="test-password-hash",
        role=UserRole.ADMIN.value,
        is_active=True
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


# --------------------------------
# FASTAPI TEST CLIENT
# --------------------------------

@pytest.fixture
def client(test_engine, test_user):

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False
    )

    def override_get_db():

        with TestingSessionLocal() as session:
            yield session

    original_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[get_db] = override_get_db

    app.dependency_overrides[get_current_user] = (
        lambda: test_user
    )

    try:
        with TestClient(app) as test_client:
            yield test_client

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


# --------------------------------
# CUSTOMER CREATION HELPER
# --------------------------------

@pytest.fixture
def make_customer(db_session):

    def _make_customer(
        user_id=None,
        display_name="Test Customer",
        company_name="Test Company",
        billing_email="customer@example.com",
        is_active=True
    ):

        customer = Customer(
            user_id=user_id,
            display_name=display_name,
            company_name=company_name,
            billing_email=billing_email,
            is_active=is_active
        )

        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        return customer

    return _make_customer

# --------------------------------
# ROLE-SPECIFIC TEST USERS
# --------------------------------

@pytest.fixture
def role_users(db_session, test_user):

    staff = User(
        email="staff@example.com",
        password_hash="test-password-hash",
        role=UserRole.STAFF.value,
        is_active=True
    )

    customer_user = User(
        email="customer@example.com",
        password_hash="test-password-hash",
        role=UserRole.CUSTOMER.value,
        is_active=True
    )

    other_customer_user = User(
        email="other.customer@example.com",
        password_hash="test-password-hash",
        role=UserRole.CUSTOMER.value,
        is_active=True
    )

    unlinked_customer_user = User(
        email="unlinked@example.com",
        password_hash="test-password-hash",
        role=UserRole.CUSTOMER.value,
        is_active=True
    )

    db_session.add_all([
        staff,
        customer_user,
        other_customer_user,
        unlinked_customer_user
    ])

    db_session.flush()

    own_profile = Customer(
        user_id=customer_user.id,
        display_name="My Customer Profile",
        billing_email="customer.billing@example.com",
        is_active=True
    )

    other_profile = Customer(
        user_id=other_customer_user.id,
        display_name="Other Customer Profile",
        billing_email="other.billing@example.com",
        is_active=True
    )

    db_session.add_all([own_profile, other_profile])
    db_session.commit()

    return {
        "admin": test_user,
        "staff": staff,
        "customer": customer_user,
        "other_customer": other_customer_user,
        "unlinked_customer": unlinked_customer_user,
        "own_profile": own_profile,
        "other_profile": other_profile
    }


# --------------------------------
# SWITCH AUTHENTICATED TEST USER
# --------------------------------

@pytest.fixture
def auth_as():

    def _auth_as(user):
        app.dependency_overrides[get_current_user] = (
            lambda: user
        )

    return _auth_as
