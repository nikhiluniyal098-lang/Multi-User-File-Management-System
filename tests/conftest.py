import pytest
from app import create_app
from models import db

@pytest.fixture
def app(tmp_path):
    test_app = create_app({
        "TESTING": True, "SECRET_KEY": "test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.db"),
        "STORAGE_ROOT": tmp_path / "storage"
    })
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()
