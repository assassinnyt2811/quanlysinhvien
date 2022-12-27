import hashlib
from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask import Response, json, jsonify, send_file, render_template_string
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
import matplotlib.pyplot as plt
import os
import io
import MySQLdb.cursors
import datetime
import calendar
from calendar import monthrange
import pandas as pd
import numpy as np
import functools
import pdfkit
import re

app = Flask(__name__)
app.secret_key = 'La Nam'

UPLOAD_FOLDER = 'static/web'
UPLOAD_FOLDER_IMG = 'static/web/img'
SAVE_FOLDER_PDF = 'static/web/pdf'
SAVE_FOLDER_EXCEL = 'static/web/excel'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'qlsv'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['UPLOAD_FOLDER_IMG'] = UPLOAD_FOLDER_IMG
app.config['SAVE_FOLDER_PDF'] = SAVE_FOLDER_PDF
app.config['SAVE_FOLDER_EXCEL'] = SAVE_FOLDER_EXCEL

mysql = MySQL(app)

def login_required(func): # need for some router
    @functools.wraps(func)
    def secure_function(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login", next=request.url))
        return func(*args, **kwargs)

    return secure_function

@app.route("/")
@app.route("/login", methods=['GET','POST'])
def login():
    if 'username' in session.keys():
        return redirect(url_for("home"))
    
    cur = mysql.connection.cursor()
    
    if 'truong' not in session.keys():
        cur.execute("SELECT * FROM truong")
        truong = cur.fetchall()[0]
        session['truong'] = truong
    
    if request.method == 'POST':
        details = request.form
        user_name = details['username'].strip()
        password = hashlib.md5(details['current-password'].encode()).hexdigest()
        
        if user_name[:6:] == "151056":
            cur.execute("""SELECT us.*, nql.ho_ten, img.path_to_image
                FROM user us
                JOIN nguoi_quan_li nql ON nql.ma_nguoi_quan_li = us.ma_nguoi_dung 
                JOIN image_data img ON img.id_image = nql.id_image
                WHERE username=%s""",(user_name,))
            user_data = cur.fetchall()
        else:        
            cur.execute("""SELECT us.*, sv.ho_ten, img.path_to_image
                    FROM user us
                    JOIN sinh_vien sv ON sv.ma_sinh_vien = us.ma_nguoi_dung 
                    JOIN image_data img ON img.id_image = nql.id_image
                    WHERE username=%s""",(user_name,))
            user_data = cur.fetchall()
        
        if len(user_data)==0:
            return render_template('general/login.html',
                                   truong = session['truong'],
                                   user_exits='False',
                                   pass_check='False')
        
        if password != user_data[0][2]:
            return render_template('general/login.html', 
                                   truong = session['truong'],
                                   user_exits='True', 
                                   pass_check='False')
    
        my_user = user_data[0]
        
        cur.execute("""
                    UPDATE `user` 
                    SET `last_login` = CURRENT_TIMESTAMP()
                    WHERE `user`.`ma_nguoi_dung` = %s
                    """, (my_user[0],))
        session['username'] = my_user
        mysql.connection.commit()
        
        cur.execute("""
                SELECT r.role_path
                FROM role r
                JOIN role_user ru ON ru.role_id = r.role_id
                WHERE ru.id_user = %s
            """, (my_user[0], ))
        role = cur.fetchall()[0][0]
        session['role'] = role
        
        cur.execute("""
                SELECT r.role_id
                FROM role r
                JOIN role_user ru ON ru.role_id = r.role_id
                WHERE ru.id_user = %s
            """, (my_user[0], ))
        role_id = cur.fetchall()[0][0]
        session['role_id'] = role_id
        
        cur.close()
        return redirect(url_for("home"))
    return render_template('general/login.html',
                           truong = session['truong'])

@login_required
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@login_required
@app.route("/home")
def home():
    return render_template(session['role'] + 'index.html',
                    my_user = session['username'],
                    truong = session['truong'])


# -------------------------- Khoa -------------------------
@login_required
@app.route('/form_add_khoa')
def form_add_khoa():
    return "Error"

@login_required
@app.route("/view_all_khoa")
def view_all_khoa():
    cur = mysql.connection.cursor()
    
    cur.execute("""
                SELECT k.*, COUNT(n.ma_nganh)
                FROM khoa k
                JOIN nganh n ON k.ma_khoa = n.ma_khoa
                WHERE n.is_delete = 0
                """)
    cac_khoa = cur.fetchall()
    
    return render_template(session['role'] + 'khoa/view_all_khoa.html',
                           cac_khoa = cac_khoa,
                           my_user = session['username'],
                           truong = session['truong'])

@login_required
@app.route("/view_khoa/<string:ma_khoa>")
def view_khoa(ma_khoa):
    cur = mysql.connection.cursor()
    
    cur.execute("""
                SELECT *
                FROM khoa k
                where k.ma_khoa = %s
                """, (ma_khoa, ))
    khoa = cur.fetchall()
    
    if (len(khoa) == 0):
        return "Error"
    
    cur.execute("""
                SELECT n.ma_nganh, n.ten_nganh, n.hinh_thuc_dao_tao,
                lh.ma_he, lh.ten_he, lh.hoc_phi_tin_chi,
                FROM nganh n 
                JOIN loai_he lh ON lh.ma_he = n.ma_he
                WHERE n.is_delete = 0 AND n.ma_khoa = %s
                """, (ma_khoa, ))
    cac_nganh = cur.fetchall()
    
    return render_template(session['role'] + 'khoa/view_khoa.html',
                           khoa = khoa,
                           cac_nganh = cac_nganh,
                           my_user = session['username'],
                           truong = session['truong'])
    
# -------------------------- Khoa -------------------------


# -------------------------- Nganh -------------------------

@login_required
@app.route('/view_all_nganh')
def view_all_nganh():
    cur = mysql.connection.cursor()
    
    cur.execute("""
                SELECT n.ma_nganh, n.ten_nganh, n.hinh_thuc_dao_tao, k.ten_khoa, lh.ten_he
                FROM nganh n
                JOIN khoa k ON k.ma_khoa = n.ma_khoa
                JOIN loai_he lh ON lh.ma_he = n.ma_he
                WHERE n.is_delete = 0
                """)
    cac_nganh = cur.fetchall()
    
    return render_template(session['role'] + 'nganh/view_all_nganh.html',
                           cac_nganh = cac_nganh,
                           my_user = session['username'],
                           truong = session['truong'])

@login_required
@app.route('/view_nganh/<string:ma_nganh>')
def view_nganh(ma_nganh):
    cur = mysql.connection.cursor()
    
    cur.execute("""
                SELECT *
                FROM nganh n
                WHERE n.is_delete = 0 AND n.ma_nganh = %s
                """, (ma_nganh, ))
    nganh = cur.fetchall()
    
    return render_template(session['role'] + 'nganh/view_nganh.html',
                           nganh = nganh,
                           my_user = session['username'],
                           truong = session['truong'])
# -------------------------- Nganh -------------------------


# -------------------------- Sinh vien -------------------------

@login_required
@app.route("/bang_sinh_vien")
def bang_sinh_vien():
    cur = mysql.connection.cursor()
    return render_template('sinhvien/bang_sinh_vien.html',
                           my_user = session['username'],
                           truong = session['truong'])  

"""
    - View table sinh vien:
        SELECT sv.ma_sinh_vien, img.path_to_img, sv.ho_ten, sv.gioi_tinh, 
        FROM sinh_vien sv
        JOIN sinh_vien_lop svl ON sv.ma_sinh_vien = svl.ma_sinh_vien
        JOIN lop l ON svl.ma_lop = l.ma_lop
        JOIN khoa k ON l.ma_khoa = k.ma_khoa
        JOIN nganh n ON l.ma_nganh = n.ma_nganh
        JOIN loai_he h ON n.ma_he = h.ma_he
        JOIN image_data img ON sv.id_image = img.id_image
        WHERE sv.is_delete == 0
        
"""
# -------------------------- Sinh vien -------------------------