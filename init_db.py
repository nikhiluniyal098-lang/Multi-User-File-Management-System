from app import app
from models import db
from models.entities import User

with app.app_context():
    db.create_all()
    # Create an initial admin only when credentials are supplied explicitly.
    import os
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    username = os.getenv("ADMIN_USERNAME", "admin")
    if email and password and not User.query.filter_by(email=email).first():
        admin = User(username=username, email=email, role="ADMIN")
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
    print("Database tables are ready.")
