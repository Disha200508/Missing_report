# MPIS - Missing Person Identification System

## Folder structure
mpis/
  backend/
    app.py            <- Flask server + REST API + database (run this)
    face_engine.py    <- MTCNN + FaceNet face matching
    requirements.txt
    face_model.pt     <- (optional) copy from your train.py output
  frontend/
    index.html
    css/style.css
    js/app.js

## Run
cd backend
pip install -r requirements.txt
pip install facenet-pytorch --no-deps
python app.py
Open http://localhost:5000

Staff login: admin / admin123   (change it:  set ADMIN_PASSWORD=yourpassword  before first run)
Delete backend/mpis.db to reset the database.
