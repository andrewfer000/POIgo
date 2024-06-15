from flask import Flask, render_template, request, redirect, g, jsonify
from flask_login import login_required, current_user, login_user, logout_user
from models import UserModel, db, login, SavedLocationsModel, UploadedImagesModel, SharedModel, NotesModel
from difflib import SequenceMatcher
import numpy as np
import os
import requests, json, itertools, re
from werkzeug.utils import secure_filename
#from flask_mail import Mail, Message
#from itsdangerous import URLSafeTimedSerializer
import traceback
import time
import urllib
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = 'xyz'
app.config['REGISTER_ENABLED'] = True
app.config['REGISTER_KEY_REQUIRED'] = False
app.config['REGISTER_KEY'] = ''

# Max Upload Size
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
# SQlite database location and options
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Google Maps API Key
app.config['GOOGLE_MAPS_APIKEY'] = 'YOUR_API_KEY_HERE'
#app.app_context().push()
db.init_app(app)
# User image upload location relarive to app.py
app.config['UPLOAD_FOLDER'] = 'static/uploads'
# Permitted file extensions for upload. All other files will be discarded.
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])


login.init_app(app)
login.login_view = 'login'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

"""
This function re-scans the address to see if the address matches. It must be called from another function that scans the address
"""
def getAddressMatch(address):
        api_key = app.config['GOOGLE_MAPS_APIKEY']

        url = f'https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}'
        response = requests.get(url)
        json_response = response.json()

        if json_response['status'] == 'OK':
            streetnum = json_response['results'][0]['address_components'][0]['long_name']
            streetname = json_response['results'][0]['address_components'][1]['short_name']
            address = json_response['results'][0]['formatted_address']

            doesitmatch = locationmatch(address, streetnum)
        return doesitmatch


"""
Takes in the address and street number seperately. This checks to see if you already have the
address saved in your bookmarks already.
"""
def locationmatch(address, streetnum):
    locations = SavedLocationsModel.query.join(UserModel, UserModel.id == SavedLocationsModel.userid).filter(current_user.get_id() == SavedLocationsModel.userid)
    matchlocation = 0
    for location in locations:
        addressmatch = [address,location.address]
        similarity = lambda x: np.mean([SequenceMatcher(None, a,b).ratio() for a,b in itertools.combinations(x, 2)])
        streetnumfound = False
        addressfound = False
        addresssplit = location.address.split()
        addresssplit2 = address.split()
        result = set(addresssplit) & set(addresssplit2)


        if len(result) >= len(addresssplit) * 0.60:
            addressfound = True

        if streetnum in addresssplit:
            streetnumfound = True

        if location.address == address or streetnumfound and addressfound and (similarity(addressmatch)) > 0.73:
            matchlocation = 1

    return matchlocation

"""
THIS CODE BELOW DOES NOT WORK!
@app.before_first_request
def create_all():
    db.create_all()
"""
"""
Login function. It takes a username and password and returs a login token.
"""
@app.route('/login', methods = ['POST', 'GET'])
def login():
    if 'application/json' in request.headers.get('Accept'):
        if request.method == 'POST':
            auth = request.get_json()
            if not auth or not auth.get('email') or not auth.get('password'):
                return jsonify({"error": "No login info provided"})
            else:
                email = auth.get('email')
                user = UserModel.query.filter_by(email = email).first()
                if user is not None and user.check_password(auth.get('password')):
                    login_user(user)
                    return jsonify({"notice": "Log in success"})
                else:
                     return jsonify({"error": "Log in failed"})
        else:
            if current_user.is_authenticated:
                return jsonify({"notice": "Session is already active!"})
            else:
                return jsonify({"notice": "Login not vaild please log in again!"})
    else:
        if current_user.is_authenticated:
            return redirect('/')

        if request.method == 'POST':
            email = request.form['email']
            user = UserModel.query.filter_by(email = email).first()
            if user is not None and user.check_password(request.form['password']):
                login_user(user)
                return redirect('/')

        return render_template('login.html')

"""
Register for a new account. Takes in an Email, Username, and password. Checks the username and email for duplicates. Rejects if the username or email matches an existing record.
"""
@app.route('/register', methods=['POST', 'GET'])
def register():
    if app.config['REGISTER_ENABLED'] == True:
        if 'application/json' in request.headers.get('Accept'):
            if current_user.is_authenticated:
                return jsonify({"notice": "You are already authenticated"})


            if request.method == 'POST':
                auth = request.get_json()
                if auth.get('regkey') == app.config['REGISTER_KEY'] or app.config['REGISTER_KEY_REQUIRED'] == False:
                    if not auth or not auth.get('email') or not auth.get('password'):
                        return jsonify({"error": "No login info provided"})
                    else:
                        email = auth.get('email')
                        username = auth.get('username')
                        password = auth.get('password')


                    if UserModel.query.filter_by(email=email).first():
                            return jsonify({"error": "Email already present"})
                    if UserModel.query.filter_by(username=username).first():
                            return jsonify({"error": "Username already present"})

                    user = UserModel(email=email, username=username)
                    user.set_password(password)
                    db.session.add(user)
                    db.session.commit()
                    return jsonify({"Notice": "Account has been created. Please login"})
                else:
                    return jsonify({"Warning": "Registration Key Required or Incorrect"})
            return jsonify({"error": "This endpoint is post only for APIs"})

        else:
            if current_user.is_authenticated:
                return redirect('/')

            if request.method == 'POST':
                if request.form['regkey'] == app.config['REGISTER_KEY'] or app.config['REGISTER_KEY_REQUIRED'] == False:
                    email = request.form['email']
                    username = request.form['username']
                    password = request.form['password']

                    if UserModel.query.filter_by(email=email).first():
                            return ('Email already Present')
                    if UserModel.query.filter_by(username=username).first():
                            return ('Username already Present')

                    user = UserModel(email=email, username=username)
                    user.set_password(password)
                    db.session.add(user)
                    db.session.commit()
                    return redirect('/login')
                else:
                    return jsonify({"Warning": "Registration Key Required or Incorrect"})
            return render_template('register.html')
    else:
        if 'application/json' in request.headers.get('Accept'):
            return jsonify({"error": "Public registration is currently disabled. Please contact the admin"})
        else:
            return jsonify({"error": "Public registration is currently disabled. Please contact the admin"})

"""
Logs the user out by revoking their token
"""

@app.route('/logout')
def logout():
    if 'application/json' in request.headers.get('Accept'):
        logout_user()
        return jsonify({"notice": "You have been logged out!"})
    else:
        logout_user()
        return redirect('/')


"""
The default route. Will automaticly teake them to search
"""
@app.route('/', methods=('GET', 'POST'))
@login_required
def search():
    if request.method == 'POST':
        address = request.form['address']

        if not address:
           return('Please enter a valid address.')
        else:
            return redirect(f"/geocode?address={address}")
    return render_template('search.html', mapsapikey=app.config['GOOGLE_MAPS_APIKEY'])


"""
This function searches the address using the google map API and returns the Lat, Lng, Address, and other information about the location.
"""
@app.route('/geocode', methods=['GET'])
@login_required
def geocode():
    api_key = app.config['GOOGLE_MAPS_APIKEY']
    raddress = quote(request.args.get('address'))
    saddress = request.args.get('address')
    url = f'https://maps.googleapis.com/maps/api/geocode/json?address={raddress}&key={api_key}'
    response = requests.get(url)
    json_response = response.json()
    g.user = current_user.get_id()

    if json_response['status'] == 'OK':
        raddress = quote(json_response['results'][0]['formatted_address'])
        url = f'https://maps.googleapis.com/maps/api/geocode/json?address="{raddress}"&key={api_key}'
        response2 = requests.get(url)
        json_response2 = response2.json()

        if json_response2['status'] == 'OK':
            lat = json_response2['results'][0]['geometry']['location']['lat']
            lng = json_response2['results'][0]['geometry']['location']['lng']
            placeid = json_response2['results'][0]['place_id']
            streetnum = json_response2['results'][0]['address_components'][0]['long_name']
            streetname = json_response2['results'][0]['address_components'][1]['short_name']
            address = json_response['results'][0]['formatted_address']

            static_map_url = f'https://maps.googleapis.com/maps/api/staticmap?center={lat},{lng}&zoom=15&size=600x300&markers={lat},{lng}&key={api_key}'
            street_view_url = f'https://maps.googleapis.com/maps/api/streetview?size=600x300&location={lat},{lng}&key={api_key}'

            matchlocation = locationmatch(address, streetnum)

        if 'application/json' in request.headers.get('Accept'):
            return jsonify(latitude=lat, longitude=lng, static_map_url=static_map_url, street_view_url=street_view_url, address=address, placeid=placeid, userid=g.user, matchlocation=matchlocation, saddress=saddress)
        else:
            return render_template('geocode.html', latitude=lat, longitude=lng, static_map_url=static_map_url, street_view_url=street_view_url, address=address, placeid=placeid, userid=g.user, matchlocation=matchlocation, saddress=saddress)
    else:
        if 'application/json' in request.headers.get('Accept'):
            return jsonify(error=json_response['status'])
        else:
            error = json_response['status']
            return render_template('geocode.html', error=error)


"""
Quires the database for the user's saved locations. This will then return a template that has a table of the locations and a map with pins.
If you use a JSON API it will return the information from the Database for the the user's location.'
"""
@app.route('/saved', methods=['POST','GET'])
@login_required
def saved():
    g.user = current_user.get_id()
    if 'application/json' in request.headers.get('Accept'):
        if request.method == 'POST':
            location = request.get_json()
            if not location or not location.get('name') or not location.get('address'):
                return jsonify({"error": "You need to provide at least a name and address"})
            else:
                location_googlemapsid = location.get('googlemapsid')
                location_usergivenname = location.get('name')
                location_address = location.get('address')
                location_userdescription = location.get('description')
                location_lat = location.get('lat')
                location_lng = location.get('lng')
                #location_saved = location.get('saved')

                location_saved = getAddressMatch(location_address)

                try:
                    if int(location_saved) == 0:
                        new_location = SavedLocationsModel(userid=g.user, googlemapsid=location_googlemapsid, usergivenname=location_usergivenname, address=location_address,  userdescription=location_userdescription, lat=location_lat, lng=location_lng)
                        db.session.add(new_location)
                        db.session.commit()
                        return jsonify({"Notice": "New Location Saved Successfully!"})
                    else:
                        return jsonify({"Notice": "Location Already saved!"})
                except:
                    return jsonify({"Error": "There was an error with your request. Did you set the saved varaible to a 1 or 0?"})
        else:
            locations = SavedLocationsModel.query.join(UserModel, UserModel.id == SavedLocationsModel.userid).filter(current_user.get_id() == SavedLocationsModel.userid)
            locationslist = []
            for location in locations:
                location.id = dict(id = location.id, name = location.usergivenname, description = location.userdescription, address = location.address, lat=location.lat, lng=location.lng)
                locationslist.append(location.id)
            return jsonify(locations=locationslist)
    else:
        if request.method == 'POST':
            location_googlemapsid = request.form['googlemapsid']
            location_usergivenname = request.form['usergivenname']
            location_address = request.form['address']
            location_userdescription = request.form['userdescription']
            location_lat = request.form['lat']
            location_lng = request.form['lng']
            saddress = request.form['saddress']

            new_location = SavedLocationsModel(userid=g.user, googlemapsid=location_googlemapsid, usergivenname=location_usergivenname, address=location_address,  userdescription=location_userdescription, lat=location_lat, lng=location_lng, saddress=saddress)

            try:
                db.session.add(new_location)
                db.session.commit()
                return redirect('/saved')
            except:
                return 'There was an error while adding the location'
        else:
            locations = SavedLocationsModel.query.join(UserModel, UserModel.id == SavedLocationsModel.userid).filter(current_user.get_id() == SavedLocationsModel.userid)
            return render_template("saved.html", locations=locations, mapsapikey=app.config['GOOGLE_MAPS_APIKEY'])

"""
THis function updates a saved location. It can change the Location name and Description
"""
@app.route('/updatelocation/<int:id>', methods=['GET','POST'])
@login_required
def update(id):
    location = SavedLocationsModel.query.get_or_404(id)
    if 'application/json' in request.headers.get('Accept'):
            if int(current_user.get_id()) == int(location.userid):
                if request.method == 'POST':
                    getlocation = request.get_json()
                    if not getlocation or not getlocation.get('name') or not getlocation.get('address'):
                        return jsonify({"error": "You need to provide at least a name and the address."})
                    else:
                        location.googlemapsid = getlocation.get('googlemapsid')
                        location.usergivenname = getlocation.get('name')
                        location.address = getlocation.get('address')
                        location.userdescription = getlocation.get('description')
                        location_lat = location.get('lat')
                        location_lng = location.get('lng')

                        try:
                            db.session.commit()
                            return jsonify({"Notice": "Location Updated!"})
                        except:
                            traceback.print_exc()
                            return jsonify({"Error": "There was an issue while updating that location"})
                else:
                    return jsonify({"name":location.usergivenname, "description":location.userdescription, "address":location.address, "googlemapsid":location.googlemapsid, "lat":location.lat, "lng":location.lng})
            else:
                return jsonify({"Error": "You cannot update a location that isn't yours!"})
    else:
        if int(current_user.get_id()) == int(location.userid):
            if request.method == 'POST':
                    location.googlemapsid = request.form['googlemapsid']
                    location.usergivenname = request.form['usergivenname']
                    location.address = request.form['address']
                    location.userdescription = request.form['userdescription']
                    location_lat = request.form['lat']
                    location_lng = request.form['lng']

                    try:
                        db.session.commit()
                        return redirect('/saved')
                    except:
                        return 'There was an issue while updating that location'
            else:
                return render_template('updatelocation.html', location=location)
        else:
            return 'You cannot update a location that is not yours!'

"""
This function deletes the location from the user's Saved Locations.'
"""
@app.route('/deletelocation/<int:id>')
@login_required
def delete(id):
    location_to_delete = SavedLocationsModel.query.get_or_404(id)
    if 'application/json' in request.headers.get('Accept'):
        if int(current_user.get_id()) == int(location_to_delete.userid):
            images = UploadedImagesModel.query.filter(current_user.get_id() == UploadedImagesModel.userid).filter(UploadedImagesModel.locationid == id)
            for image in images:
                try:
                    image_to_delete = UploadedImagesModel.query.get_or_404(image.id)
                    filename = image_to_delete.filename
                    db.session.delete(image_to_delete)
                    db.session.commit()
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    except:
                        print("Image file now found but still deleting database entry!")
                except:
                    print("There was an error deleting an image for thhis location")

            shares = SharedModel.query.filter(current_user.get_id() == SharedModel.userid).filter(SharedModel.locationid == id)
            for share in shares:
                try:
                    share_to_delete = SharedModel.query.get_or_404(share.id)
                    db.session.delete(share_to_delete)
                    db.session.commit()
                except:
                    print("There was an error deleting an image for thhis location")
            try:
                db.session.delete(location_to_delete)
                db.session.commit()
                return jsonify({"Notice": "Location Successfully Deleted"})
            except:
                return  jsonify({"Error": "There was an error deleting that location"})
        else:
            return  jsonify({"Error": "You cannot delete a location that isn't yours!"})
    else:
        if int(current_user.get_id()) == int(location_to_delete.userid):
            images = UploadedImagesModel.query.filter(current_user.get_id() == UploadedImagesModel.userid).filter(UploadedImagesModel.locationid == id)
            for image in images:
                try:
                    image_to_delete = UploadedImagesModel.query.get_or_404(image.id)
                    filename = image_to_delete.filename
                    db.session.delete(image_to_delete)
                    db.session.commit()
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    except:
                        print("Image file now found but still deleting database entry!")
                except:
                    print("There was an error deleting an image for thhis location")

            shares = SharedModel.query.filter(current_user.get_id() == SharedModel.userid).filter(SharedModel.locationid == id)
            for share in shares:
                try:
                    share_to_delete = SharedModel.query.get_or_404(share.id)
                    db.session.delete(share_to_delete)
                    db.session.commit()
                except:
                    print("There was an error deleting an image for thhis location")

            notepads = NotesModel.query.filter(id == NotesModel.locationid)
            for notepad in notepads:
                try:
                    notepad_to_delete = NotesModel.query.get_or_404(notepad.id)
                    db.session.delete(notepad_to_delete)
                    db.session.commit()
                except:
                    print("There was an error deleting the notepads for thhis location")

            try:
                db.session.delete(location_to_delete)
                db.session.commit()
                return redirect('/saved')
            except:
                return 'There was an error while deleting that location'
        else:
            return 'You cannot delete a location that is not yours!'

@app.route('/manageaccount/<int:id>', methods=['GET','POST'])
@login_required
def manageaccount(id):
    if 'application/json' in request.headers.get('Accept'):
        if id == int(current_user.get_id()):
            if request.method == 'POST':
                jsonuser = request.get_json()
                getuser = UserModel.query.get_or_404(id)
                email = jsonuser.get("email")
                username = jsonuser.get("username")
                password = jsonuser.get("password")
                oldpassword = jsonuser.get("oldpassword")


                if UserModel.query.filter_by(email=email).first() and getuser.email != email:
                    return jsonify({"error": "Email already present"})

                if UserModel.query.filter_by(username=username).first() and getuser.username != username:
                    return jsonify({"error": "Username already present"})

                if getuser is not None and getuser.check_password(oldpassword) and email and username and password:
                    getuser.username = username
                    getuser.email = email
                    getuser.set_password(password)
                    db.session.commit()
                    return jsonify({"Notice" : 'Account Updated Successfully'})
                else:
                    return jsonify({"Error" : "Cannot update your user. Is your old password incorrect?"})
            else:
                getuser = UserModel.query.get_or_404(id)
                return jsonify({ "username" : getuser.username, "email" : getuser.email, "id" : id, "password" : ""})
        else:
            return jsonify({"Error" : "You cannot update a user that is not yours!"})
    else:
        if id == int(current_user.get_id()):
            if request.method == 'POST':
                    getuser = UserModel.query.get_or_404(id)
                    email = request.form['email']
                    username = request.form['username']
                    password = request.form['password']
                    oldpassword = request.form['oldpassword']

                    if UserModel.query.filter_by(email=email).first() and getuser.email != email:
                        return "Email already present"

                    if UserModel.query.filter_by(username=username).first() and getuser.username != username:
                        return "Username already present"


                    if getuser is not None and getuser.check_password(request.form['oldpassword']):
                        getuser.username = username
                        getuser.email = email
                        getuser.set_password(password)
                        db.session.commit()
                        return 'Account Updated Successfully'
                    else:
                        return "Cannot update your user. Is your old password incorrect?"
            else:
                getuser = UserModel.query.get_or_404(id)
                return render_template('manageaccount.html', username = getuser.username, email = getuser.email, id=id)
        else:
            return "You cannot edit somone else's account"


@app.route('/deleteaccount/<int:id>', methods=['GET','POST'])
@login_required
def deleteaccount(id):
    if 'application/json' in request.headers.get('Accept'):
        getuser = UserModel.query.get_or_404(id)
        if id == int(current_user.get_id()) and getuser.id == id:
            if request.method == 'POST':
                jsonuser = request.get_json()
                if getuser.check_password(jsonuser.get('password')):
                    userslocations = SavedLocationsModel.query.join(UserModel, UserModel.id == SavedLocationsModel.userid).filter(current_user.get_id() == SavedLocationsModel.userid)
                    for userlocation in userslocations:
                        images = UploadedImagesModel.query.filter(current_user.get_id() == UploadedImagesModel.userid).filter(UploadedImagesModel.locationid == userlocation.id)
                        for image in images:
                            try:
                                image_to_delete = UploadedImagesModel.query.get_or_404(image.id)
                                filename = image_to_delete.filename
                                db.session.delete(image_to_delete)
                                db.session.commit()
                                try:
                                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                                except:
                                    print("Image file now found but still deleting database entry!")
                            except:
                                print("There was an error deleting an image for thhis location")

                        shares = SharedModel.query.filter(current_user.get_id() == SharedModel.userid).filter(SharedModel.locationid == userlocation.id)
                        for share in shares:
                            try:
                                share_to_delete = SharedModel.query.get_or_404(share.id)
                                db.session.delete(share_to_delete)
                                db.session.commit()
                            except:
                                print("There was an error deleting a share for thhis location")

                        myshareds = SharedModel.query.filter(current_user.get_id() == SharedModel.shareduserid)
                        for myshared in myshareds:
                            try:
                                shared_to_delete = SharedModel.query.get_or_404(myshared.id)
                                db.session.delete(shared_to_delete)
                                db.session.commit()
                            except:
                                print("There was an error deleting a share for you for thhis location")

                        notepads = NotesModel.query.filter(current_user.get_id() == NotesModel.userid)
                        for notepad in notepads:
                            try:
                                notepad_to_delete = NotesModel.query.get_or_404(notepad.id)
                                db.session.delete(notepad_to_delete)
                                db.session.commit()
                            except:
                                print("There was an error deleting a notepad for thhis location")

                        try:
                            location_to_delete = SavedLocationsModel.query.get_or_404(userlocation.id)
                            db.session.delete(location_to_delete)
                            db.session.commit()
                        except:
                            return jsonify({"Error": 'There was an error while deleting that location'})
                    try:
                        db.session.delete(getuser)
                        db.session.commit()
                    except:
                        return jsonify({"Error": 'There was an error while deleting that user'})
                    return jsonify({"Notice": 'Your account has been deleted.'})
                else:
                    return jsonify({"Error": 'Password Incorrect, Your account is safe!'})
            else:
                return jsonify({ "username" : getuser.username, "email" : getuser.email})
        else:
            return jsonify({"Error": 'You cannot delete a user that is not yours!'})
    else:
        getuser = UserModel.query.get_or_404(id)
        if id == int(current_user.get_id()) and getuser.id == id:
            if request.method == 'POST':
                if getuser.check_password(request.form['password']):
                    userslocations = SavedLocationsModel.query.join(UserModel, UserModel.id == SavedLocationsModel.userid).filter(current_user.get_id() == SavedLocationsModel.userid)
                    for userlocation in userslocations:
                        images = UploadedImagesModel.query.filter(current_user.get_id() == UploadedImagesModel.userid).filter(UploadedImagesModel.locationid == userlocation.id)
                        for image in images:
                            try:
                                image_to_delete = UploadedImagesModel.query.get_or_404(image.id)
                                filename = image_to_delete.filename
                                db.session.delete(image_to_delete)
                                db.session.commit()
                                try:
                                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                                except:
                                    print("Image file now found but still deleting database entry!")
                            except:
                                print("There was an error deleting an image for thhis location")

                        shares = SharedModel.query.filter(current_user.get_id() == SharedModel.userid).filter(SharedModel.locationid == userlocation.id)
                        for share in shares:
                            try:
                                share_to_delete = SharedModel.query.get_or_404(share.id)
                                db.session.delete(share_to_delete)
                                db.session.commit()
                            except:
                                print("There was an error deleting a share for thhis location")

                        myshareds = SharedModel.query.filter(current_user.get_id() == SharedModel.shareduserid)
                        for myshared in myshareds:
                            try:
                                shared_to_delete = SharedModel.query.get_or_404(myshared.id)
                                db.session.delete(shared_to_delete)
                                db.session.commit()
                            except:
                                print("There was an error deleting a share for you for thhis location")

                        notepads = NotesModel.query.filter(current_user.get_id() == NotesModel.userid)
                        for notepad in notepads:
                            try:
                                notepad_to_delete = NotesModel.query.get_or_404(notepad.id)
                                db.session.delete(notepad_to_delete)
                                db.session.commit()
                            except:
                                print("There was an error deleting a notepad for thhis location")


                        try:
                            location_to_delete = SavedLocationsModel.query.get_or_404(userlocation.id)
                            db.session.delete(location_to_delete)
                            db.session.commit()
                        except:
                            return 'There was an error while deleting that user'
                    try:
                        db.session.delete(getuser)
                        db.session.commit()
                    except:
                        return 'There was an error while deleting that user'
                    return redirect('/logout')
                else:
                    return 'Password incorrect, Your user is safe!'
            else:
                return render_template('deleteuser.html', username = getuser.username, email = getuser.email)
        else:
            return 'You cannot delete a user that is not yours!'


@app.route('/images/<int:locationid>', methods=('GET', 'POST'))
@login_required
def images(locationid):
    location = SavedLocationsModel.query.get_or_404(locationid)
    if 'application/json' in request.headers.get('Accept'):
        if int(current_user.get_id()) == int(location.userid):
            userid = current_user.get_id()
            images = UploadedImagesModel.query.filter(current_user.get_id() == UploadedImagesModel.userid, UploadedImagesModel.locationid == locationid)
            imageslist = []
            for image in images:
                image.id = dict(id = image.id, userid = image.userid, locationid = image.locationid, filename = image.filename, alttext = image.alttext)
                imageslist.append(image.id)
            return jsonify(iamges=imageslist)
        else:
            return  jsonify({'Error': 'You cannot view locations that do not belong to you!'})
    else:
        if int(current_user.get_id()) == int(location.userid):
            userid = current_user.get_id()
            images = UploadedImagesModel.query.filter(current_user.get_id() == userid).filter(UploadedImagesModel.locationid == locationid)
            return render_template('images.html', images=images, locationid=locationid)
        else:
            return "You cannot view locations that do not belong to you!"

@app.route('/uploadimages/<int:locationid>', methods=('GET', 'POST'))
@login_required
def uploadimages(locationid):
    location = SavedLocationsModel.query.get_or_404(locationid)
    if 'application/json' in request.headers.get('Accept'):
        if int(current_user.get_id()) == int(location.userid):
            if request.method == 'POST':
                # check if the post request has the file part
                if 'file' not in request.files:
                    return jsonify({"Error": 'No file part!'})

                file = request.files['file']
                alttext = "User uploaded image of location"

                if file.filename == '':
                    return jsonify({"Error": 'No file selected!'})

                if file and allowed_file(file.filename):
                    filename = f'{current_user.get_id()}-{file.filename}'
                    fileupload = UploadedImagesModel(userid = int(current_user.get_id()), locationid = locationid, filename=filename, alttext=alttext)
                    db.session.add(fileupload)
                    db.session.commit()
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    return jsonify({"Notice": 'File Upload Success'})
            else:
                return jsonify({"Error": 'This endpoint is POST only!'})
        else:
            return jsonify({"Error": 'You cannot upload to locations that are not yours!'})
    else:
        if int(current_user.get_id()) == int(location.userid):
            if request.method == 'POST':
                if 'file' not in request.files:
                    print("file not in request This is the error")
                    return redirect(f"/uploadimages/{locationid}")
                file = request.files['file']
                alttext = "User uploaded image of location"

                if file.filename == '':
                    print("Not Image!")
                    return redirect(request.url)
                if file and allowed_file(file.filename):
                    filename = f'{current_user.get_id()}-{file.filename}'
                    fileupload = UploadedImagesModel(userid = int(current_user.get_id()), locationid = locationid, filename=filename, alttext=alttext)
                    db.session.add(fileupload)
                    db.session.commit()
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    return redirect(f'/images/{locationid}')
                else:
                    print("Not allowed!")
                    return redirect(f"/uploadimages/{locationid}")
            else:
                return render_template('upload.html', locationid=locationid)
        else:
            return 'You cannot upload to locations that are not yours!'



@app.route('/deleteimage/<int:id>', methods=('GET', 'POST'))
@login_required
def deleteimages(id):
    if 'application/json' in request.headers.get('Accept'):
        if request.method == 'POST':
            image_to_delete = UploadedImagesModel.query.get_or_404(id)
            if int(current_user.get_id()) == int(image_to_delete.userid):
                locationid = image_to_delete.locationid
                imageid = image_to_delete.id

                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image_to_delete.filename))
                except:
                    print("Image file now found but still deleting database entry!")
                try:
                    db.session.delete(image_to_delete)
                    db.session.commit()

                    sharedlocations = SharedModel.query.filter(SharedModel.locationid == locationid)
                    for sharedlocation in sharedlocations:
                        otherdata = json.loads(sharedlocation.otherdata)
                        sharedimages = otherdata['sharedpics']

                        if str(imageid) in sharedimages:
                            sharedimages.remove(str(imageid))
                            sharedlocation.userid = sharedlocation.userid
                            sharedlocation.locationid = sharedlocation.locationid
                            sharedlocation.shareduserid = sharedlocation.shareduserid
                            sharedlocation.sharedwithusername = sharedlocation.sharedwithusername
                            sharedlocation.otherdata = str(json.dumps(otherdata))
                            db.session.commit()

                    return jsonify({"Notice": "Image Successfully Deleted"})
                except:
                    return  jsonify({"Error": "There was an error deleting that image"})
            else:
                return  jsonify({"Error": "You cannot delete an image that isn't yours!"})
        else:
             return  jsonify({"Error": "This endpoint is POST only!"})
    else:
        if request.method == 'POST':
            image_to_delete = UploadedImagesModel.query.get_or_404(id)
            if int(current_user.get_id()) == int(image_to_delete.userid):
                locationid = image_to_delete.locationid
                imageid = image_to_delete.id

                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image_to_delete.filename))
                except:
                    print("Image file now found but still deleting database entry!")
                try:
                    db.session.delete(image_to_delete)
                    db.session.commit()

                    sharedlocations = SharedModel.query.filter(SharedModel.locationid == locationid)
                    for sharedlocation in sharedlocations:
                        otherdata = json.loads(sharedlocation.otherdata)
                        sharedimages = otherdata['sharedpics']

                        if str(imageid) in sharedimages:
                            sharedimages.remove(str(imageid))
                            sharedlocation.userid = sharedlocation.userid
                            sharedlocation.locationid = sharedlocation.locationid
                            sharedlocation.shareduserid = sharedlocation.shareduserid
                            sharedlocation.sharedwithusername = sharedlocation.sharedwithusername
                            sharedlocation.otherdata = str(json.dumps(otherdata))
                            db.session.commit()

                    return redirect(f'/images/{locationid}')
                except:
                    traceback.print_exc()
                    return 'There was an error while deleting that image'

            else:
                return 'You cannot delete an image that is not yours!'
        else:
            return 'This endpoint is a post only!'


@app.route('/share/<int:id>', methods=('GET', 'POST'))
@login_required
def share(id):
    location = SavedLocationsModel.query.get_or_404(id)
    if 'application/json' in request.headers.get('Accept'):
        if int(current_user.get_id()) == int(location.userid):
            if request.method == 'POST':
                jsondata = request.get_json()
                username = jsondata.get("username")
                locationid = str(id);
                try:
                    alreadysharednum = 0
                    users = UserModel.query.filter(username == UserModel.username)
                    for user in users:
                        sharedwithuserid = user.id
                        sharedwithusername = user.username

                    alreadyshareds = SharedModel.query.filter(locationid == SharedModel.locationid).filter(sharedwithuserid == SharedModel.shareduserid)
                    for alreadyshared in alreadyshareds:
                        alreadysharednum = alreadysharednum + 1

                    if alreadysharednum > 0:
                        return jsonify({"Notice": "You have already shared this location with this user!"})
                    else:
                        sharedpics = list()
                        sharedpads = list()
                        otherdata = {"sharedpics" : sharedpics, "sharedpads" : sharedpads}
                        sharedlocation = SharedModel(userid=current_user.get_id(), locationid=locationid, shareduserid=sharedwithuserid, sharedwithusername = sharedwithusername, otherdata=str(json.dumps(otherdata)))
                        db.session.add(sharedlocation)
                        db.session.commit()

                except:
                    traceback.print_exc()
                    return jsonify({"Error": "Failed to find user. Are you sure you typed their username right?"})

                return jsonify({"Notice": "Shared with user Successfully"})
            else:
                sharedwiths = SharedModel.query.filter(SharedModel.locationid == id)
                sharelist = []
                for sharedwith in sharedwiths:
                    sharedaddadd = dict(id = sharedwith.id, locationid=sharedwith.locationid, sharedwithuserid = sharedwith.sharedwithuserid, sharedwithusername = sharedwith.sharedwithusername, otherdata=str(json.dumps(otherdata)))
                    locationsdata.append(sharelist)
                    return jsonify({"Shared With": sharelist})

    else:
        if int(current_user.get_id()) == int(location.userid):
            if request.method == 'POST':
                username = request.form['username']
                locationid = str(id);
                try:
                    alreadysharednum = 0
                    users = UserModel.query.filter(username == UserModel.username)
                    for user in users:
                        sharedwithuserid = user.id
                        sharedwithusername = user.username

                    alreadyshareds = SharedModel.query.filter(locationid == SharedModel.locationid).filter(sharedwithuserid == SharedModel.shareduserid)
                    for alreadyshared in alreadyshareds:
                        alreadysharednum = alreadysharednum + 1

                    if alreadysharednum > 0:
                        return "You have already shared this location with this user!"
                    else:
                        sharedpics = list()
                        sharedpads = list()
                        otherdata = {"sharedpics" : sharedpics, "sharedpads" : sharedpads}
                        sharedlocation = SharedModel(userid=current_user.get_id(), locationid=locationid, shareduserid=sharedwithuserid, sharedwithusername = sharedwithusername, otherdata=str(json.dumps(otherdata)))
                        db.session.add(sharedlocation)
                        db.session.commit()

                except:
                    traceback.print_exc()
                    return "Failed to find user. Are you sure you typed their username right?"


                sharedwith = SharedModel.query.filter(SharedModel.locationid == id)
                return render_template('share.html', id=id, location=location, sharedwith=sharedwith)
            else:
                sharedwith = SharedModel.query.filter(SharedModel.locationid == id)

                return render_template('share.html', id=id, location=location, sharedwith=sharedwith)

        else:
            return "You cannot share a location that is not yours!"

@app.route('/deleteshare/<int:id>', methods=('GET', 'POST'))
@login_required
def deleteshare(id):
    share = SharedModel.query.get_or_404(id)
    if 'application/json' in request.headers.get('Accept'):
        if int(current_user.get_id()) == int(share.userid) or int(current_user.get_id()) == int(share.shareduserid):
            if request.method == 'POST':
                userid = int(share.userid)
                locationid = share.locationid
                db.session.delete(share)
                db.session.commit()
                return  jsonify({"Notice": "Share deleted"})
            else:
                return "This endpoint is POST only!"
        else:
            return jsonify({"Error": "You cannot delete a share that is not yours!"})
    else:
        if int(current_user.get_id()) == int(share.userid) or int(current_user.get_id()) == int(share.shareduserid):
            if request.method == 'POST':
                userid = int(share.userid)
                locationid = share.locationid
                db.session.delete(share)
                db.session.commit()
                if int(current_user.get_id()) == userid:
                    return redirect(f"/share/{locationid}")
                else:
                    return redirect(f"/viewshare")
            else:
                return "This endpoint is POST only!"
        else:
            return "You cannot delete a share that is not yours!"


@app.route('/viewshare', methods=('GET', 'POST'))
@login_required
def viewshare():
    locationsdata = []
    sharedlocations = SharedModel.query.filter(current_user.get_id() == SharedModel.shareduserid)
    for sharedlocation in sharedlocations:
        locations = SavedLocationsModel.query.filter(sharedlocation.locationid == SavedLocationsModel.id)
        sharedfroms = UserModel.query.filter(sharedlocation.userid == UserModel.id)
        for sharedfrom in sharedfroms:
            usershared = sharedfrom.username
        for location in locations:
            locationadd = dict(id = location.id, name = location.usergivenname, description = location.userdescription, address = location.address, lat=location.lat, lng=location.lng, shareid=sharedlocation.id, usershared=usershared)
            locationsdata.append(locationadd)

    if 'application/json' in request.headers.get('Accept'):
        return  jsonify({"Locations": locationsdata, "mapsapikey" : app.config['GOOGLE_MAPS_APIKEY']})
    else:
        return render_template('shared.html', locations=locationsdata, mapsapikey=app.config['GOOGLE_MAPS_APIKEY'])

@app.route('/sharedimages/<int:id>', methods=('GET', 'POST'))
@login_required
def sharedimages(id):
    sharedlocations = SharedModel.query.filter(id == SharedModel.id)
    for sharedlocation in sharedlocations:
        if int(current_user.get_id()) == int(sharedlocation.shareduserid):
            locations = SavedLocationsModel.query.filter(sharedlocation.locationid == SavedLocationsModel.id)
            otherdata = json.loads(sharedlocation.otherdata)
            sharedimages = otherdata['sharedpics']
            sharedimages = [int(i) for i in sharedimages]
            for location in locations:
                imagestoshow = []
                images =  UploadedImagesModel.query.filter(location.id == UploadedImagesModel.locationid)
                for image in images:
                    if image.id in sharedimages:
                        imageadd = dict(id = image.id, userid = image.userid, filename = image.filename, alttext = image.alttext)
                        imagestoshow.append(imageadd)

        else:
            return "You cannot view locations images for locations not shared with you!"

    if 'application/json' in request.headers.get('Accept'):
         return  jsonify({"Shared Images": imagestoshow})
    else:
        try:
            return render_template('sharedimages.html', images=imagestoshow)
        except:
            return "There was an error processing this request"

@app.route('/shareimage/<int:id>', methods=('GET', 'POST'))
@login_required
def shareimage(id):
    sharedlocations = SharedModel.query.filter(current_user.get_id() == SharedModel.userid).filter(SharedModel.id == id)
    if request.method == 'POST':
        if 'application/json' in request.headers.get('Accept'):
            jsondata = request.get_json()
            imageid = jsondata.get('imageid')
            share = SharedModel.query.get_or_404(id)
            otherdata = json.loads(share.otherdata)
            sharedimages = otherdata['sharedpics']
        else:
            imageid = request.form['imageid']
            share = SharedModel.query.get_or_404(id)
            otherdata = json.loads(share.otherdata)
            sharedimages = otherdata['sharedpics']

        if imageid in sharedimages:
            sharedimages.remove(imageid)
            share = SharedModel.query.get_or_404(id)
            share.userid = share.userid
            share.locationid = share.locationid
            share.shareduserid = share.shareduserid
            share.sharedwithusername = share.sharedwithusername
            share.otherdata = str(json.dumps(otherdata))
            db.session.commit()
        else:
            sharedimages.append(imageid)
            share = SharedModel.query.get_or_404(id)
            share.userid = share.userid
            share.locationid = share.locationid
            share.shareduserid = share.shareduserid
            share.sharedwithusername = share.sharedwithusername
            share.otherdata = str(json.dumps(otherdata))
            db.session.commit()

        if 'application/json' in request.headers.get('Accept'):
            return jsonify({"Notice": "Share for this image have been toggled"})
        else:
             return redirect(f"/shareimage/{id}")
    else:
        for sharedlocation in sharedlocations:
            locationsdata = []
            locations = SavedLocationsModel.query.filter(sharedlocation.locationid == SavedLocationsModel.id)

            for location in locations:
                locationadd = dict(id = location.id, name = location.usergivenname, description = location.userdescription, address = location.address, lat=location.lat, lng=location.lng, shareid=sharedlocation.id)
                locationsdata.append(locationadd)
                locationid = location.id


            sharedwithid = sharedlocation.shareduserid
            otherdata = json.loads(sharedlocation.otherdata)
            locationid = sharedlocation.locationid
            sharedimages = otherdata['sharedpics']
            sharedimages = [int(i) for i in sharedimages]
            images = UploadedImagesModel.query.filter(UploadedImagesModel.locationid == locationid)

        if 'application/json' in request.headers.get('Accept'):
            return jsonify({"SharedImageIDs": sharedimages})
        else:
            return render_template('shareimages.html', sharedimages=sharedimages, images=images, id=id, locationid=locationid)


@app.route('/viewnotes/<int:id>', methods=('GET', 'POST'))
@login_required
def viewnotepads(id):
    getNotes = NotesModel.query.filter(id == NotesModel.locationid)
    location = SavedLocationsModel.query.get_or_404(id)
    if request.method == 'POST':
        print("WIP")
    else:
        if int(location.userid) == int(current_user.get_id()):
            return render_template("locationnotes.html", locationid=id, notes=getNotes)
        else:
            return "You cannot view notes for locations that are not yours."

@app.route('/deletenotepad/<int:id>', methods=('GET', 'POST'))
@login_required
def deletenotepad(id):
    getNote = NotesModel.query.get_or_404(id)
    locationid = getNote.locationid
    notepadid = getNote.id
    if int(getNote.userid) == int(current_user.get_id()):
                db.session.delete(getNote)
                db.session.commit()

                sharedlocations = SharedModel.query.filter(SharedModel.locationid == locationid)
                for sharedlocation in sharedlocations:
                    otherdata = json.loads(sharedlocation.otherdata)
                    sharedpads = otherdata['sharedpads']

                    if str(notepadid) in sharedpads:
                        sharedpads.remove(str(notepadid))
                        sharedlocation.userid = sharedlocation.userid
                        sharedlocation.locationid = sharedlocation.locationid
                        sharedlocation.shareduserid = sharedlocation.shareduserid
                        sharedlocation.sharedwithusername = sharedlocation.sharedwithusername
                        sharedlocation.otherdata = str(json.dumps(otherdata))
                        db.session.commit()

                return redirect(f"/viewnotes/{locationid}")
    else:
        return "You cannot delete a notepad that is not yours"


@app.route('/createnotepad/<int:id>', methods=('GET', 'POST'))
@login_required
def createnotepad(id):
    location = SavedLocationsModel.query.get_or_404(id)
    if int(location.userid) == int(current_user.get_id()):
        otherdata = ""
        notepad = NotesModel(userid=current_user.get_id(), locationid=id, data="", otherdata=str(json.dumps(otherdata)))
        db.session.add(notepad)
        db.session.commit()
        return redirect(f"/viewnotes/{id}")
    else:
        return "You cannot create a note for a location that is not yours."

@app.route('/notepad/<int:id>', methods=('GET', 'POST'))
@login_required
def notepad(id):
    getNote = NotesModel.query.get_or_404(id)
    if int(getNote.userid) == int(current_user.get_id()):
        if request.method == 'POST':
            content = json.loads(request.form['content'])
            getNote.userid = getNote.userid
            getNote.locationid = getNote.locationid
            getNote.data = str(json.dumps(content))
            getNote.otherdata = getNote.otherdata
            db.session.commit()
            return redirect(f"/notepad/{id}")
        else:
            try:
                content = json.loads(getNote.data)
                content = content["ops"]
                return render_template('notepad.html', content=json.dumps(content), id=id, locationid=getNote.locationid)
            except:
                return render_template("notepad.html", id=id)
    else:
        return "You cannot edit a notepad that is not yours"


@app.route('/sharenotepad/<int:id>', methods=('GET', 'POST'))
@login_required
def sharenotepad(id):
    sharedlocations = SharedModel.query.filter(current_user.get_id() == SharedModel.userid).filter(SharedModel.id == id)
    if request.method == 'POST':
        if 'application/json' in request.headers.get('Accept'):
            jsondata = request.get_json()
            notepadid = jsondata.get('notepadid')
        else:
            notepadid = request.form['notepadid']
            share = SharedModel.query.get_or_404(id)

        share = SharedModel.query.get_or_404(id)
        otherdata = json.loads(share.otherdata)
        sharedpads = otherdata['sharedpads']

        if notepadid in sharedpads:
            sharedpads.remove(notepadid)
            share = SharedModel.query.get_or_404(id)
            share.userid = share.userid
            share.locationid = share.locationid
            share.shareduserid = share.shareduserid
            share.sharedwithusername = share.sharedwithusername
            share.otherdata = str(json.dumps(otherdata))
            db.session.commit()
        else:
            sharedpads.append(notepadid)
            share = SharedModel.query.get_or_404(id)
            share.userid = share.userid
            share.locationid = share.locationid
            share.shareduserid = share.shareduserid
            share.sharedwithusername = share.sharedwithusername
            share.otherdata = str(json.dumps(otherdata))
            db.session.commit()

        if 'application/json' in request.headers.get('Accept'):
            return jsonify({"Notice": "Share for this notepad have been toggled"})
        else:
             return redirect(f"/sharenotepad/{id}")
    else:
        for sharedlocation in sharedlocations:
            locationsdata = []
            locations = SavedLocationsModel.query.filter(sharedlocation.locationid == SavedLocationsModel.id)

            for location in locations:
                locationadd = dict(id = location.id, name = location.usergivenname, description = location.userdescription, address = location.address, lat=location.lat, lng=location.lng, shareid=sharedlocation.id)
                locationsdata.append(locationadd)
                locationid = location.id


            sharedwithid = sharedlocation.shareduserid
            otherdata = json.loads(sharedlocation.otherdata)
            locationid = sharedlocation.locationid
            sharedpads = otherdata['sharedpads']
            sharedpads = [int(i) for i in sharedpads]
            notepads = NotesModel.query.filter(NotesModel.locationid == locationid)

            for notepad in notepads:
                print(notepad.id)


        if 'application/json' in request.headers.get('Accept'):
            return jsonify({"SharedPads": sharedpads})
        else:
            return render_template('sharenotepad.html', sharedpads=sharedpads, notepads=notepads, id=id, locationid=locationid)

@app.route('/sharednotepads/<int:id>', methods=('GET', 'POST'))
@login_required
def sharednotepads(id):
    sharedlocations = SharedModel.query.filter(id == SharedModel.id)
    for sharedlocation in sharedlocations:
        if int(current_user.get_id()) == int(sharedlocation.shareduserid):
            locations = SavedLocationsModel.query.filter(sharedlocation.locationid == SavedLocationsModel.id)
            otherdata = json.loads(sharedlocation.otherdata)
            sharedpads = otherdata['sharedpads']
            sharedpads = [int(i) for i in sharedpads]
            for location in locations:
                notepads =  NotesModel.query.filter(location.id == NotesModel.locationid)
                padstoshow = []
                for notepad in notepads:
                    if notepad.id in sharedpads:
                        print(notepad.id)
                        #padadd = dict(id = notepad.id, locationid=notepad.locationid, userid=notepad.userid, data=notepad.data, otherdata=notepad.otherdata, shareid=sharedlocation.id)
                        padadd = dict(id = notepad.id, locationid=notepad.locationid, userid=notepad.userid, shareid=sharedlocation.id)
                        padstoshow.append(padadd)


                print(padstoshow)

        else:
            return "You cannot view notepads not shared with you!"

    if 'application/json' in request.headers.get('Accept'):
         return  jsonify({"Shared Notepads": padstoshow})
    else:
        try:
            return render_template('sharednotepads.html', notepads=padstoshow)
        except:
            return "There was an error processing this request"



@app.route('/sharednotepad/<int:id>', methods=('GET', 'POST'))
@login_required
def sharednotepad(id):
    shareid = request.args.get('shareid')
    sharedlocations = SharedModel.query.filter(shareid == SharedModel.id)
    for sharedlocation in sharedlocations:
        if int(current_user.get_id()) == int(sharedlocation.shareduserid):
            locations = SavedLocationsModel.query.filter(sharedlocation.locationid == SavedLocationsModel.id)
            otherdata = json.loads(sharedlocation.otherdata)
            sharedpads = otherdata['sharedpads']
            sharedpads = [int(i) for i in sharedpads]
            for location in locations:
                notepads =  NotesModel.query.filter(location.id == NotesModel.locationid)
                for notepad in notepads:
                    if id in sharedpads:
                        getNote = NotesModel.query.get_or_404(id)
                        if request.method == 'POST':
                            content = json.loads(request.form['content'])
                            getNote.userid = getNote.userid
                            getNote.locationid = getNote.locationid
                            getNote.data = str(json.dumps(content))
                            getNote.otherdata = getNote.otherdata
                            db.session.commit()
                            return redirect(f"/sharednotepad/{id}?shareid={shareid}")
                        else:
                            try:
                                content = json.loads(getNote.data)
                                content = content["ops"]
                                return render_template('sharednotepad.html', content=json.dumps(content), id=id, locationid=getNote.locationid, shareid=shareid)
                            except:
                                return render_template("sharednotepad.html", id=id, shareid=shareid)
                    else:
                        return "You cannot edit a notepad that is not yours"
        else:
            return "You cannot edit a notepad that is not yours"

    return "ShareID and notepad do not match. Please try again"

if __name__ == '__main__':
    app.run(debug=True)
