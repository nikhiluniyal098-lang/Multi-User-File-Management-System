from models import db
from models.entities import User, File, FilePermission

def test_private_file_not_downloadable(client, app, tmp_path):
    with app.app_context():
        a=User(username="a",email="a@x.com"); a.set_password("password123")
        b=User(username="b",email="b@x.com"); b.set_password("password123")
        db.session.add_all([a,b]); db.session.flush()
        path=tmp_path/"storage"/"uploads"/"x.txt"; path.parent.mkdir(parents=True); path.write_text("x")
        f=File(user_id=a.id,original_filename="x.txt",stored_filename="x.txt",file_path=str(path),file_size=1)
        db.session.add(f); db.session.commit(); bid=b.id
    client.post("/login",data={"identity":"b@x.com","password":"password123"})
    assert client.get(f"/download/{f.id}").status_code == 403
