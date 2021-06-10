from bson import ObjectId
from pymongo import MongoClient
import jwt
import datetime
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

SECRET_KEY = 'daily_hanghae'

#디비 아이피 본인것으로 바꿔야 되나안되나 실험 가능해요!
client = MongoClient('52.79.249.230', 27017, username="test", password="test")
db = client.daily_hanghae


@app.route('/index')
def home():
    token_receive = request.cookies.get('mytoken')
    bool_sign_in = bool(token_receive)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]}, {"_id": False})
        return render_template('index.html', user_info=user_info, bool_sign_in=bool_sign_in)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인을 먼저 진행해주세요."))


@app.route('/')
def login():
    msg = request.args.get("msg")
    token_receive = request.cookies.get('mytoken')
    bool_sign_in = bool(token_receive)
    if bool_sign_in:
        return home()
    else:
        return render_template('login.html', msg=msg)


@app.route('/user/<username>')
def user(username):
    # 각 사용자의 프로필과 글을 모아볼 수 있는 공간
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        status = (username == payload["id"])  # 내 프로필이면 True, 다른 사람 프로필 페이지면 False

        user_info = db.users.find_one({"username": username}, {"_id": False})
        return render_template('user.html', user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route('/sign_in', methods=['POST'])
def sign_in():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()

    username_result = db.users.find_one({'username': username_receive})
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})
    if username_result is None:
        msg = "입력하신 아이디가 없습니다."
        return jsonify({'result': 'fail', 'msg': msg})
    elif (username_result is not None) & (result is None):
        msg = "아이디에 맞지 않는 비밀번호입니다. 비밀번호를 재입력해주세요."
        return jsonify({'result': 'fail', 'msg': msg})
    else:
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24 * 7),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')

        return jsonify({'result': 'success', 'token': token})


@app.route('/sign_up/save', methods=['POST'])
def sign_up():
    # 회원가입
    username_receive = request.form['username_give']
    user_name_receive = request.form['user_name_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        'username': username_receive,
        'user_name': user_name_receive,
        'password': password_hash
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})


@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})


# 게시물 리스트 보여줄거
@app.route('/daily_meal')
def daily_meal():
    meal_list = list(db.daily_meal.find({}).sort("_id", -1).limit(18))
    return render_template("daily_meal.html", meal_list=meal_list)


# 게시물 상세페이지 보러가기
@app.route('/meal_detail/<keyword>')
def meal_detail(keyword):
    clicked_meal = list(db.daily_meal.find({"_id": ObjectId(keyword)}))

    return render_template("meal_detail.html", clicked_meal=clicked_meal)


# 게시물 등록
@app.route('/daily_meal', methods=["POST"])
def save_daily_meal():
    token_receive = request.cookies.get('mytoken')

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        user_info = db.users.find_one({"username": payload["id"]})
        title_receive = request.form['title_give']
        content_receive = request.form['content_give']

        # 사진 업로드
        file = request.files["file_give"]
        extension = file.filename.split('.')[-1]
        today = datetime.now()
        mytime = today.strftime("%Y-%m-%d-%H-%M-%S")
        filename = f'file-{mytime}'
        save_to = f'{filename}.{extension}'
        file.save(f'static/meal_pics/{save_to}')

        doc = {
            "username": user_info["username"],
            "user_name": user_info["user_name"],
            'title': title_receive,
            'content': content_receive,
            'file': f'{filename}.{extension}'
        }
        db.daily_meal.insert_one(doc)
        return jsonify({"result": "success", 'msg': '글쓰기 완료!'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("daily_meal"))


# 게시물 삭제
@app.route('/api/delete_content', methods=['POST'])
def delete_content():
    token_receive = request.cookies.get('mytoken')

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        id_receive = request.form["id_give"]
        # user_info = db.daily_meal.find_one({"username" : payload["id"]})
        data_info = db.daily_meal.find_one({"_id": ObjectId(id_receive)})

        if data_info["username"] == payload["id"]:
            db.daily_meal.delete_one({"_id": ObjectId(id_receive)})
            return jsonify({'result': 'success', 'msg': "게시물 삭제 완료!"})
        else:
            return jsonify({'result': 'success', 'msg': "자신이 쓴 게시물만 삭제 가능합니다."})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("daily_meal"))


# 게시물 수정
@app.route('/api/update_content', methods=['POST'])
def update_content():
    token_receive = request.cookies.get('mytoken')
    try:
        id_receive = request.form["id_give"]
        title_receive = request.form["title_give"]
        content_receive = request.form["content_give"]

        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        data_info = db.daily_meal.find_one({"_id": ObjectId(id_receive)})

        if data_info["username"] == payload["id"]:
            db.daily_meal.update({"_id": ObjectId(id_receive)},
                                 {'$set': {"title": title_receive, "content": content_receive}})
            return jsonify({'result': 'success', 'msg': "게시물 수정 완료!"})
        else:
            return jsonify({'result': 'success', 'msg': "자신이 쓴 게시물만 수정 가능합니다."})

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("daily_meal"))

# 다이어리 리스트 페이지
@app.route('/diary_list')
def diary_list():
    diary_list = list(db.diary.find({}).sort("_id", -1))
    return render_template("diary_list.html", diary_list=diary_list)

# 다이어리 상세 페이지
@app.route('/diary/<keyword>')
def diary_detail(keyword):
    clicked_diary = list(db.diary.find({"_id": ObjectId(keyword)}))

    return render_template("diary.html", clicked_diary=clicked_diary)

# 다이어리 작성페이지
@app.route('/diary_write')
def diary_write():
    return render_template("diary_write.html")

# 다이어리 작성
@app.route('/write_diary', methods=['POST'])
def write_diary():
    token_receive = request.cookies.get('mytoken')

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        user_info = db.users.find_one({"username": payload["id"]})
        title_receive = request.form['title_give']
        content_receive = request.form['content_give']

        file = request.files["file_give"]
        extension = file.filename.split('.')[-1]
        today = datetime.now()
        mytime = today.strftime("%Y-%m-%d-%H-%M-%S")
        filename = f'file-{mytime}'
        save_to = f'{filename}.{extension}'
        file.save(f'static/diary_pics/{save_to}')

        doc = {
            "username": user_info["username"],
            "user_name": user_info["user_name"],
            'title': title_receive,
            'content': content_receive,
            'file': f'{filename}.{extension}'
        }
        db.diary.insert_one(doc)
        return jsonify({"result": "success", 'msg': '게시물 저장이 완료되었습니다!'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("diary_list"))

# 다이어리 수정
@app.route('/eidt_diary', methods=['POST'])
def edit_diary():
    token_receive = request.cookies.get('mytoken')
    try:
        id_receive = request.form["id_give"]
        title_receive = request.form["title_give"]
        content_receive = request.form["content_give"]

        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        data_info = db.diary.find_one({"_id": ObjectId(id_receive)})

        if data_info["username"] == payload["id"]:
            db.diary.update({"_id": ObjectId(id_receive)},
                            {'$set': {"title": title_receive, "content": content_receive}})
            return jsonify({'result': 'success', 'msg': "게시물 수정이 완료 되었습니다!"})
        else:
            return jsonify({'result': 'success', 'msg': "게시물 수정 권한이 없습니다!"})

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("diary_list"))

# 다이어리 삭제
@app.route('/delete_diary', methods=['POST'])
def delete_diary():
    token_receive = request.cookies.get('mytoken')

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        id_receive = request.form["id_give"]
        data_info = db.diary.find_one({"_id": ObjectId(id_receive)})

        if data_info["username"] == payload["id"]:
            db.diary.delete_one({"_id": ObjectId(id_receive)})
            return jsonify({'result': 'success', 'msg': "게시물 삭제가 완료 되었습니다!"})
        else:
            return jsonify({'result': 'success', 'msg': "게시물 삭제 권한이 없습니다!"})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("diary_list"))


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)