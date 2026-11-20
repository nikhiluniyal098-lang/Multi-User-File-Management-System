from models import db
from models.entities import User

def test_transaction_commit_and_rollback(app):
    with app.app_context():
        u=User(username="commit",email="c@x.com"); u.set_password("password123")
        db.session.add(u); db.session.commit()
        assert User.query.filter_by(username="commit").count()==1
        try:
            db.session.add(User(username="rollback",email="r@x.com"))
            db.session.flush()
            raise RuntimeError("simulate failure")
        except RuntimeError:
            db.session.rollback()
        assert User.query.filter_by(username="rollback").count()==0
