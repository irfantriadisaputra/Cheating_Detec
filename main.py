import sqlite3
import subprocess
from flask import Flask, make_response, jsonify, render_template,session,Response
from flask_restx import Resource, Api, reqparse
from flask_cors import  CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import jwt, os,random
from flask_mail import Mail, Message
# import torch
import cv2
from PIL import Image

app = Flask(__name__)
api = Api(app)
CORS(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://root:@127.0.0.1:3306/dbcheatdetec"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'whateveryouwant'
# mail env config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = "detectioncheating@gmail.com"
app.config['MAIL_PASSWORD'] = "okushjfgivzmtulh"
mail = Mail(app)
# mail env config
db = SQLAlchemy(app)

class Users(db.Model):
    id       = db.Column(db.Integer(), primary_key=True, nullable=False)
    nama     = db.Column(db.String(30), nullable=False)
    email    = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    is_verified = db.Column(db.Boolean(),nullable=False)
    createdAt = db.Column(db.Date)
    updatedAt = db.Column(db.Date)


# Email functions
# https://medium.com/@stevenrmonaghan/password-reset-with-flask-mail-protocol-ddcdfc190968
# https://www.youtube.com/watch?v=g_j6ILT-X0k
# https://stackoverflow.com/questions/72547853/unable-to-send-email-in-c-sharp-less-secure-app-access-not-longer-available

# @app.route('/visual')
# def visual():
#     return render_template('visual.html')

# @app.route('/streamlit', methods=['GET'])
# def run_streamlit():
#         # Run the Streamlit application as a separate process
#     output = subprocess.Popen(['streamlit', 'run', 'my_streamlite1.py'])
#     return jsonify({'output': output})

# @app.route('/realtime')
# def realtime():
#     return render_template('video.html')

# def detect_objects():
#     # Load the YOLOv5 model with .pt weights
#     model = torch.hub.load('ultralytics/yolov5', 'custom', path='model/menyontek.pt', force_reload=True)

#     # Open camera
#     cap = cv2.VideoCapture(0)

#     # Connect to the SQLite database
#     conn = sqlite3.connect('data.db')
#     cursor = conn.cursor()

#     # Create a table if it doesn't exist
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS detections (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             label TEXT,
#             confidence REAL
#         )
#     ''')
#     conn.commit()

#     while True:
#         # Read frame from the camera
#         ret, frame = cap.read()

#         if ret:
#             frame = cv2.flip(frame, 1)

#             # Convert frame to PIL Image
#             image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
#             # Perform inference on the image
#             results = model(image)

#             # Get detection results
#             pred_boxes = results.xyxy[0]

#             # Draw bounding boxes and labels on the frame
#             for *xyxy, conf, cls in pred_boxes:
#                 x1, y1, x2, y2 = map(int, xyxy)
#                 label = f'{model.names[int(cls)]} {conf:.2f}'
#                 cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
#                 cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

#                 # Insert detection into the database
#                 cursor.execute('INSERT INTO detections (label, confidence) VALUES (?, ?)', (label, conf))
#                 conn.commit()

#             # Convert the frame back to BGR format
#             frame = cv2.cvtColor(frame, cv2.WINDOW_NORMAL)

#             # Encode the frame as JPEG
#             ret, buffer = cv2.imencode('.jpg', frame)

#             if not ret:
#                 continue

#             # Yield the frame as a byte array
#             yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'

#         else:
#             break

#     # Release the camera and clean up
#     cap.release()

#     # Close the database connection
#     cursor.close()
#     conn.close()

# @app.route('/video_feed')
# def video_feed():
#     return Response(detect_objects(), mimetype='multipart/x-mixed-replace; boundary=frame')

#parserRegister
regParser = reqparse.RequestParser()
regParser.add_argument('nama', type=str, help='nama', location='json', required=True)
regParser.add_argument('email', type=str, help='Email', location='json', required=True)
regParser.add_argument('password', type=str, help='Password', location='json', required=True)
regParser.add_argument('confirm_password', type=str, help='Confirm Password', location='json', required=True)


@api.route('/register')
class Registration(Resource):
    @api.expect(regParser)
    def post(self):
        # BEGIN: Get request parameters.
        args        = regParser.parse_args()
        nama        = args['nama']
        email       = args['email']
        password    = args['password']
        password2   = args['confirm_password']
        is_verified = False

        # cek confirm password
        if password != password2:
            return {
                'messege': 'Password tidak cocok'
            }, 400

        #cek email sudah terdaftar
        user = db.session.execute(db.select(Users).filter_by(email=email)).first()
        if user:
            return "Email sudah terpakai silahkan coba lagi menggunakan email lain"
        user          = Users()
        user.nama     = nama
        user.email    = email
        user.password = generate_password_hash(password)
        user.is_verified = is_verified
        db.session.add(user)
        msg = Message(subject='Verification OTP',sender=os.environ.get("MAIL_USERNAME"),recipients=[user.email])
        token =  random.randrange(10000,99999)
        session['email'] = user.email
        session['token'] = str(token)
        msg.html=render_template(
        'verify_email.html', token=token)
        mail.send(msg)
        db.session.commit()
        return {'message':
            'Registrasi Berhasil. Silahkan cek email untuk verifikasi.'}, 200

otpparser = reqparse.RequestParser()
otpparser.add_argument('otp', type=str, help='otp', location='json', required=True)
@api.route('/verify')
class Verify(Resource):
    @api.expect(otpparser)
    def post(self):
        args = otpparser.parse_args()
        otp = args['otp']
        if 'token' in session:
            sesion = session['token']
            if otp == sesion:
                email = session['email']

                user = Users.query.filter_by(email=email).first()
                user.is_verified = True
                db.session.commit()
                session.pop('token',None)
                return {'message' : 'Email berhasil diverifikasi'}, 200
            else:
                return {'message' : 'Kode Otp Salah'},400
        else:
            return {'message' : 'Kode Otp Salah'},400
        
logParser = reqparse.RequestParser()
logParser.add_argument('email', type=str, help='Email', location='json', required=True)
logParser.add_argument('password', type=str, help='Password', location='json', required=True)

@api.route('/login')
class LogIn(Resource):
    @api.expect(logParser)
    def post(self):
        args        = logParser.parse_args()
        email       = args['email']
        password    = args['password']
        # cek jika kolom email dan password tidak terisi
        if not email or not password:
            return {
                'message': 'Email Dan Password Harus Diisi'
            }, 400
        #cek email sudah ada
        user = db.session.execute(
            db.select(Users).filter_by(email=email)).first()
        if not user:
            return {
                'message': 'Email / Password Salah'
            }, 400
        else:
            user = user[0]
        #cek password
        if check_password_hash(user.password, password):
            if user.is_verified == True:
                token= jwt.encode({
                        "user_id":user.id,
                        "user_email":user.email,
                        "exp": datetime.utcnow() + timedelta(hours= 1)
                },app.config['SECRET_KEY'],algorithm="HS256")
                return {'message' : 'Login Berhasil',
                        'token' : token
                        },200
            else:
                return {'message' : 'Email Belum Diverifikasi ,Silahka verifikasikan terlebih dahulu '},401
        else:
            return {
                'message': 'Email / Password Salah'
            }, 400

def decodetoken(jwtToken):
    decode_result = jwt.decode(
               jwtToken,
               app.config['SECRET_KEY'],
               algorithms = ['HS256'],
            )
    return decode_result

authParser = reqparse.RequestParser()
authParser.add_argument('Authorization', type=str, help='Authorization', location='headers', required=True)
@api.route('/detail-user')
class DetailUser(Resource):
       @api.expect(authParser)
       def get(self):
        args = authParser.parse_args()
        bearerAuth  = args['Authorization']
        try:
            jwtToken    = bearerAuth[7:]
            token = decodetoken(jwtToken)
            user =  db.session.execute(db.select(Users).filter_by(email=token['user_email'])).first()
            user = user[0]
            data = {
                'nama' : user.nama,
                'email' : user.email
            }
        except:
            return {
                'message' : 'Token Tidak valid,Silahkan Login Terlebih Dahulu!'
            }, 401

        return data, 200

editParser = reqparse.RequestParser()
editParser.add_argument('nama', type=str, help='nama', location='json', required=True)
editParser.add_argument('Authorization', type=str, help='Authorization', location='headers', required=True)
@api.route('/edit-user')
class EditUser(Resource):
       @api.expect(editParser)
       def put(self):
        args = editParser.parse_args()
        bearerAuth  = args['Authorization']
        nama = args['nama']
        datenow =  datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        try:
            jwtToken    = bearerAuth[7:]
            token = decodetoken(jwtToken)
            user = Users.query.filter_by(email=token.get('user_email')).first()
            user.nama = nama
            user.updatedAt = datenow
            db.session.commit()
        except:
            return {
                'message' : 'Token Tidak valid,Silahkan Login Terlebih Dahulu!'
            }, 401
        return {'message' : 'Update User Sukses'}, 200


verifyParser = reqparse.RequestParser()
verifyParser.add_argument(
    'otp', type=str, help='OTP', location='json', required=True)

#editpasswordParser
editPasswordParser =  reqparse.RequestParser()
editPasswordParser.add_argument('current_password', type=str, help='current_password',location='json', required=True)
editPasswordParser.add_argument('new_password', type=str, help='new_password',location='json', required=True)
@api.route('/edit-password')
class Password(Resource):
    @api.expect(authParser,editPasswordParser)
    def put(self):
        args = editPasswordParser.parse_args()
        argss = authParser.parse_args()
        bearerAuth  = argss['Authorization']
        cu_password = args['current_password']
        newpassword = args['new_password']
        try:
            jwtToken    = bearerAuth[7:]
            token = decodetoken(jwtToken)
            user = Users.query.filter_by(id=token.get('user_id')).first()
            if check_password_hash(user.password, cu_password):
                user.password = generate_password_hash(newpassword)
                db.session.commit()
            else:
                return {'message' : 'Password Lama Salah'},400
        except:
            return {
                'message' : 'Token Tidak valid! Silahkan, Sign in!'
            }, 401
        return {'message' : 'Password Berhasil Diubah'}, 200

if __name__ == '__main__':
    # app.run(ssl_context='adhoc', debug=True)
    app.run(host='192.168.43.170', port=5000, debug=True)