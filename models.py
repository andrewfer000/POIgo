from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager

login = LoginManager()
db = SQLAlchemy()

class UserModel(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(80), unique=True)
    username = db.Column(db.String(100))
    password_hash = db.Column(db.String())
    #otherdata = db.Column(db.String(4096))

    def set_password(self,password):
        self.password_hash = generate_password_hash(password)

    def check_password(self,password):
        return check_password_hash(self.password_hash,password)

class SavedLocationsModel(db.Model):
    __tablename__ = 'saved_locations'

    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey('users.id'))
    googlemapsid = db.Column(db.String(80))
    usergivenname = db.Column(db.String(80))
    address = db.Column(db.String(180))
    userdescription = db.Column(db.String(3072))
    lat = db.Column(db.String(16))
    lng = db.Column(db.String(16))
    #otherdata = db.Column(db.String(4096))

class  UploadedImagesModel(db.Model):
    __tablename__ = 'uploaded_images'

    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey('users.id'))
    locationid = db.Column(db.Integer, db.ForeignKey('saved_locations.id'))
    filename = db.Column(db.String(128))
    alttext = db.Column(db.String(512))
    #otherdata = db.Column(db.String(4096))

class  SharedModel(db.Model):
    __tablename__ = 'shared_locations'

    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey('users.id'))
    locationid = db.Column(db.Integer, db.ForeignKey('saved_locations.id'))
    shareduserid = db.Column(db.Integer, db.ForeignKey('users.id'))
    sharedwithusername = db.Column(db.String(100))
    otherdata = db.Column(db.String(4096))

class  NotesModel(db.Model):
    __tablename__ = 'nodepads'

    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey('users.id'))
    locationid = db.Column(db.Integer, db.ForeignKey('saved_locations.id'))
    data = db.Column(db.String(32768))
    otherdata = db.Column(db.String(4096))

@login.user_loader
def load_user(id):
    return UserModel.query.get(int(id))
