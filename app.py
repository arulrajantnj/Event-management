from flask import Flask, render_template, request, redirect, session, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import qrcode
import os
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "event_management_secret_key"


app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    "DATABASE_URL",
    "sqlite:///event.db"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =========================
# DATABASE MODEL
# =========================

class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reg_id = db.Column(db.String(20), unique=True)

    name = db.Column(db.String(100))
    mobile = db.Column(db.String(20))
    email = db.Column(db.String(100))

    district = db.Column(db.String(100))
    organization = db.Column(db.String(200))
    designation = db.Column(db.String(100))
    category = db.Column(db.String(50))

    attendance = db.Column(db.String(20), default="Absent")

    reg_date = db.Column(db.DateTime, default=datetime.utcnow)

# =========================
# HOME
# =========================

@app.route('/')
def home():
    return render_template('index.html')

# =========================
# REGISTRATION
# =========================

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        count = Participant.query.count() + 1
        reg_id = f"EVT2026{count:05d}"

        participant = Participant(
            reg_id=reg_id,
            name=request.form['name'],
            mobile=request.form['mobile'],
            email=request.form['email'],
            district=request.form['district'],
            organization=request.form['organization'],
            designation=request.form['designation'],
            category=request.form['category']
        )

        db.session.add(participant)
        db.session.commit()

        os.makedirs("qrcodes", exist_ok=True)

        qr_data = f"""
Registration ID: {reg_id}
Name: {participant.name}
Mobile: {participant.mobile}
"""

        qr = qrcode.make(qr_data)
        qr_path = f"qrcodes/{reg_id}.png"
        qr.save(qr_path)

        return render_template('success.html', participant=participant)

    return render_template('register.html')

# =========================
# LOGIN
# =========================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        if username == "admin" and password == "admin123":
            session['admin'] = True
            return redirect('/admin')

        return "Invalid Username or Password"

    return render_template('login.html')

# =========================
# LOGOUT
# =========================

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# =========================
# ADMIN DASHBOARD
# =========================

@app.route('/admin')
def admin():

    if not session.get('admin'):
        return redirect('/login')

    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    query = Participant.query

    if search:
        query = query.filter(
            (Participant.name.contains(search)) |
            (Participant.mobile.contains(search)) |
            (Participant.reg_id.contains(search))
        )

    participants = query.order_by(
        Participant.id.desc()
    ).paginate(page=page, per_page=50, error_out=False)

    total = Participant.query.count()

    teachers = Participant.query.filter_by(category="Teacher").count()
    students = Participant.query.filter_by(category="Student").count()
    volunteers = Participant.query.filter_by(category="Volunteer").count()
    guests = Participant.query.filter_by(category="Guest").count()

    return render_template(
        'admin.html',
        participants=participants,
        search=search,
        total=total,
        teachers=teachers,
        students=students,
        volunteers=volunteers,
        guests=guests
    )

# =========================
# ATTENDANCE
# =========================

@app.route('/attendance/<int:id>')
def attendance(id):

    if not session.get('admin'):
        return redirect('/login')

    participant = Participant.query.get_or_404(id)
    participant.attendance = "Present"

    db.session.commit()

    return redirect('/admin')

# =========================
# QR CODE VIEW
# =========================

@app.route('/qrcode/<reg_id>')
def qrcode_view(reg_id):
    path = f"qrcodes/{reg_id}.png"
    return send_file(path)

# =========================
# CERTIFICATE
# =========================

@app.route('/certificate/<int:id>')
def certificate(id):

    if not session.get('admin'):
        return redirect('/login')

    participant = Participant.query.get_or_404(id)

    os.makedirs("certificates", exist_ok=True)

    pdf_path = f"certificates/{participant.reg_id}.pdf"

    c = canvas.Canvas(pdf_path)

    c.setFont("Helvetica-Bold", 24)
    c.drawString(180, 750, "CERTIFICATE")

    c.setFont("Helvetica", 14)
    c.drawString(100, 680, f"This certifies that {participant.name}")
    c.drawString(100, 650, "has successfully participated in the event.")

    c.save()

    return send_file(pdf_path, as_attachment=True)

# =========================
# EXPORT EXCEL
# =========================

@app.route('/export')
def export():

    if not session.get('admin'):
        return redirect('/login')

    participants = Participant.query.all()

    data = []
    for p in participants:
        data.append({
            "Reg ID": p.reg_id,
            "Name": p.name,
            "Mobile": p.mobile,
            "Email": p.email,
            "District": p.district,
            "Organization": p.organization,
            "Designation": p.designation,
            "Category": p.category,
            "Attendance": p.attendance
        })

    df = pd.DataFrame(data)
    file_name = "participants.xlsx"
    df.to_excel(file_name, index=False)

    return send_file(file_name, as_attachment=True)

# =========================
# START APP
# =========================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
    
if __name__ == "__main__":
    app.run()