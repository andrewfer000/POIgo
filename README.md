# POIgo
This project started as a Capstone Project for C&amp;I at Rowan University. POIgo is an advanced multi-user web based address book which can store locations, photos, and even multiple rich text notepads for saved locations which can be shared with other users on the system. Some possible uses of POIgo are Construction Site Management, Customer location management, Realestate, Travel planning, and more! 

Please note you will need to obtain a FREE google maps API key to use this application. Google gives everyone $200 in Maps API credits per month which is plenty for 10 or less regular users. Support for other APIs may come in the future.  

Registration is open by default. However you can close this registration or require a registration key to be used during sign up in order to protect your instance.

## Future Goals (2024 and Beyond)
Since I may start using this at my job, I'd like to improve POIgo. This includes:
1. Fixing bugs and making the application more stable
2. Improving the UI and making the frontend more functional
3. Email verifcation for new users and maybe passwordless login. 2FA functionality with some kind of authenticator would be nice too.
4. Global Configuration File for variables such as the API key, Database, and other stuff
5. Postgres and MySQL support for more capability and enterprise use.
6. Docker Image?
7. Move all map data stuff into one place. This will hopefully allow extending to other APIs such as Apple Maps.


## Features that are planned to be removed in the near future
1. Image uploads, Since notpads support images and the current image implmentation is insecure. May replace with some sort of file storage (ie Text documents, Images, Etc.) stored directly in the database.

## Original POIgo Team
- Andrew Ferdetta (Backend Enginner &amp; Full Stack Developer, Testing)
- Johnathan McCabe (Documentation and Front End Devleoper)
- Joseph Tomphpson (Front End Devleoper)
- Seden Agar (Graphics Design, Logo, CSS, and Testing)

# How to get up and running-

WINDOWS Virtual Enviornment:
```
git clone https://github.com/andrewfer000/POIgo.git
cd POIgo-master
python -m venv POIgo
POIgo\Scripts\activate.bat
pip install flask
pip install numpy
pip install flask_sqlalchemy
pip install flask_login
pip install requests
```

Linux & MacOS Virtual Enviornment
```
git clone https://github.com/andrewfer000/POIgo.git
cd POIgo-master
python -m venv POIgo
source POIgo/bin/activate
pip install flask
pip install numpy
pip install flask_sqlalchemy
pip install flask_login
pip install requests
```

Database Setup (First time)
1. Make sure you are in the Virtual Environment
2. Enter the python shell by running `python`

In Python Shell:
```
from app import app
from app import db
app.app_context().push()
db.create_all()
exit() 
```

**IMPORTANT:** Insert your Google Maps API key in `app.py`


Run the app:

```
python app.py
```

# First Login
1. Go to localhost:5000 or your server address if you are running it in the cloud.
2. Register for an account. You need a username and password and enter the registration key if you set one in the config
3. Login and start using POIgo! To test your API Key, try searching for an address.   

# Starting After Setup 
When you want to run POIgo after setup, All you need to do is
1. Activate the virtual Environment using either the `source` command on Linux or run the `activate.bat` script on Windows
2. Run `python app.py` in the POIgo root directory


# POIgo's Code History
This is our second repo. The original development was private. We made a decision to make a new repository for the public code due to private information such as hashed passwords and API keys being accessable in the old repository. If you are interested in POIgo's hisotry before this please reach out to me.
