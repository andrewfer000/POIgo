# POIgo
This project started as a Capstone Project for C&amp;I at Rowan University.

Original POIgo Team
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
pip install request
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
pip install request
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

Run the app:

```
python app.py
```

# After Setup
When you want to run POIgo after setup, All you need to do is
1. Activate the virtual Environment using either the `source` command on Linux or run the `activate.bat` script on Windows
2. Run `python app.py` in the POIgo root directory
