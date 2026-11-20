from models.entities import User
from models import db

def test_registration_and_password_hash(client, app):
    response = client.post("/register", data={"username":"alice","email":"a@example.com","password":"password123"}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="a@example.com").first()
        assert user is not None and user.password_hash != "password123"
        assert user.check_password("password123")

def test_dashboard_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
