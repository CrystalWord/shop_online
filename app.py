import os, re, random, json, urllib.parse, urllib.request,datetime,math
from flask import Flask, render_template, request, jsonify, session,abort,redirect,url_for,Response
import pymysql

conf = json.load(open("server_conf.json"))  # 加载配置信息
conn =pymysql.connect(
    host=conf["db_server_ip"],
    port=conf["db_server_port"],
    user=conf["db_user"],
    passwd=conf["db_password"],
    db=conf["db_name"],
    charset ='utf8'
)


app = Flask(__name__)
app.secret_key = b'N\x1cI\xcf6\xe1\x98\xa1\x06\x0c\x8f\x05\xf7\xca\xe6\xa0H0\xa7B\xfc\xde\xd7i'

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login_handle():
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        uname = request.form.get("uname")
        upass = request.form.get("upass")
        
        if not (uname and uname.strip() and upass and upass.strip()):
            abort(Response("登录失败"))
 
        if not re.fullmatch("[a-zA-Z0-9_]{4,20}",uname):
            abort(Response("用户名不合法!"))

        if not(len(upass) >= 6 and len(upass) <= 16):
            abort(Response("密码格式错误！"))

        with conn.cursor() as cur:
            cur.execute("SELECT * from shop_user where uname=%s and upass=md5(%s)", (uname,uname+upass))
            res = cur.fetchone()
            
        if res:
            #登录成功跳转个人中心
            cur_login_time = datetime.datetime.now()
            user_info = {
                "uid":res[0],
                "uname":res[1],
                "upass":res[2],
                "phone":res[3],
                
                "reg_time":res[4],
                "last_login_time":res[5],
                "priv":res[6],
                "state":res[7],
                "login_time": cur_login_time
            }

            
            session["user_info"] = user_info

            try:
                with conn.cursor() as cur:
                    cur.execute("update shop_user set last_login_time=%s where uid=%s ",(cur_login_time,res[0]))
                    conn.commit()
                return redirect(url_for("index"))
            except Exception as e:
                print(e)
        
        else:
            #登录失败

            return render_template("login.html",login_fail=1)



@app.route("/reg", methods=["GET", "POST"])
def reg_handle():
    if request.method == "GET":
        return render_template("reg.html")
    elif request.method == "POST":
        uname = request.form.get("uname")
        upass = request.form.get("upass")
        upass2 = request.form.get("upass2")
        phone = request.form.get("phone")
        verify_code = request.form.get("verify_code")
        

        if not (uname and uname.strip() and upass and upass2 and phone and verify_code):
            abort(500)
 
        if not re.fullmatch("[a-zA-Z0-9_]{4,20}",uname):
            abort(Response("用户名不合法!"))
        
        with conn.cursor() as cur:
            cur.execute("SELECT uid from shop_user where uname=%s", (uname,))
            if cur.rowcount != 0:
                abort(Response("用户名已经被注册!"))

        if not(len(upass) >= 6 and len(upass) <= 16 and upass == upass2):
            abort(Response("密码格式错误！"))
 
        if  session.get(phone) != verify_code:
            abort(Response("验证码错误!"))

      

        try:
            with conn.cursor() as cur:
                cur.execute("insert into shop_user values(DEFAULT, %s, md5(%s), %s, sysdate(), sysdate(), 1, 1)",(uname,uname + upass,phone))
                conn.commit()
        except:
            abort(Response("注册失败！"))  

        session.pop(phone)  
        return redirect(url_for("login_handle"))


@app.route("/logout")  #注销
def logout_handle():
    res = {"err": 1,"desc":"未登录！"}
    if session.get("user_info"):
        session.pop("user_info")
        res["err"] = 0
        res["desc"] = "注销成功！"
    return jsonify(res)





@app.route("/send_sms_code")
def send_sms_code_handle():
    phone = request.args.get("phone")

    result = {"err": 1, "desc": "内部错误！"}
    # verify_code = send_sms_code(phone)  #发送验证码
    verify_code = "1234"
    if verify_code:
        # 发送短信验证码成功
        session[phone] = verify_code
        
        result["err"] = 0
        result["desc"] = "发送短信验证码成功！"

    return jsonify(result)

def send_sms_code(phone):
    '''
    函数功能：发送短信验证码（6位随机数字）
    函数参数：
    phone 接收短信验证码的手机号
    返回值：发送成功返回验证码，失败返回False
    '''
    verify_code = str(random.randint(100000, 999999))

    try:
        url = "http://v.juhe.cn/sms/send"
        params = {
            "mobile": phone,  # 接受短信的用户手机号码
            "tpl_id": "162901",  # 您申请的短信模板ID，根据实际情况修改
            "tpl_value": "#code#=%s" % verify_code,  # 您设置的模板变量，根据实际情况修改
            "key": "ab75e2e54bf3044898459cb209b195e4",  # 应用APPKEY(应用详细页查询)
        }
        params = urllib.parse.urlencode(params).encode()

        f = urllib.request.urlopen(url, params)
        content = f.read()
        res = json.loads(content)
        
        print(res)

        if res and res['error_code'] == 0:
            return verify_code
        else:
            return False
    except:
        return False   



if __name__ == "__main__":
    app.run(port=80, debug=True)
