#!/usr/bin/env python3
"""Driver Dignity: stdlib Python + SQLite backend. Run: python server.py"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from http.cookies import SimpleCookie
from hmac import compare_digest
import json, sqlite3, os, re, datetime, secrets, hashlib, smtplib, ssl, threading, time
from email.message import EmailMessage
ROOT=Path(__file__).resolve().parent
DB=Path(os.environ.get('DRIVER_DIGNITY_DB',str(ROOT/'driver_dignity.db')))
PORT=int(os.environ.get('PORT','8000'))
ADMIN_PASSWORD=os.environ.get('ADMIN_PASSWORD','')
SESSIONS={}
LOCK=threading.Lock()
RATE={}
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def db():
 c=sqlite3.connect(DB,timeout=15)
 c.row_factory=sqlite3.Row
 c.execute('PRAGMA busy_timeout=15000')
 c.execute('CREATE TABLE IF NOT EXISTS submissions (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL, name TEXT NOT NULL, email TEXT NOT NULL, city TEXT, role TEXT, interest TEXT, message TEXT NOT NULL, created_at TEXT NOT NULL)')
 c.execute('CREATE TABLE IF NOT EXISTS respect_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, message TEXT NOT NULL, status TEXT NOT NULL DEFAULT "pending", created_at TEXT NOT NULL)')
 c.commit();return c
def notify(subject,body):
 host=os.environ.get('SMTP_HOST');to=os.environ.get('NOTIFY_EMAIL');sender=os.environ.get('SMTP_FROM')
 if not (host and to and sender):return
 def send():
  try:
   msg=EmailMessage();msg['Subject']=subject;msg['From']=sender;msg['To']=to;msg.set_content(body)
   with smtplib.SMTP(host,int(os.environ.get('SMTP_PORT','587')),timeout=12) as smtp:
    smtp.starttls(context=ssl.create_default_context())
    if os.environ.get('SMTP_USER'):smtp.login(os.environ['SMTP_USER'],os.environ.get('SMTP_PASSWORD',''))
    smtp.send_message(msg)
  except Exception as e:print('Notification failed:',type(e).__name__)
 threading.Thread(target=send,daemon=True).start()
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
 def end_headers(self):
  self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','strict-origin-when-cross-origin');self.send_header('X-Frame-Options','DENY');self.send_header('Content-Security-Policy',"frame-ancestors 'none'")
  super().end_headers()
 def reply(self,status,payload,cookie=None):
  b=json.dumps(payload,ensure_ascii=False).encode('utf8');self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store')
  if cookie:self.send_header('Set-Cookie',cookie)
  self.end_headers();self.wfile.write(b)
 def data(self):
  length=int(self.headers.get('Content-Length','0'))
  if length<2 or length>16000:raise ValueError('Invalid request size')
  if 'application/json' not in self.headers.get('Content-Type',''):raise ValueError('Expected JSON')
  d=json.loads(self.rfile.read(length))
  if not isinstance(d,dict):raise ValueError('Invalid payload')
  return d
 def authorized(self):
  cookie=SimpleCookie()
  try:cookie.load(self.headers.get('Cookie',''))
  except Exception:return False
  token=cookie.get('dd_session');token=token.value if token else ''
  with LOCK:return bool(token and token in SESSIONS and SESSIONS[token]>time.time())
 def limited(self):
  ip=self.client_address[0];t=time.monotonic()
  with LOCK:
   RATE[ip]=[x for x in RATE.get(ip,[]) if t-x<60]
   if len(RATE[ip])>=15:return True
   RATE[ip].append(t)
   if len(RATE)>5000:RATE.clear()
  return False
 def do_GET(self):
  path=urlparse(self.path).path
  if path=='/api/respect':
   try:offset=min(10000,max(0,int(parse_qs(urlparse(self.path).query).get('offset',['0'])[0])))
   except ValueError:offset=0
   with db() as c:rows=c.execute('SELECT name,message FROM respect_messages WHERE status=? ORDER BY id DESC LIMIT 6 OFFSET ?',('approved',offset)).fetchall()
   return self.reply(200,{'messages':[dict(x) for x in rows]})
  if path=='/api/admin/session':return self.reply(200,{'authenticated':self.authorized(),'configured':bool(ADMIN_PASSWORD)})
  if path=='/api/admin/data':
   if not self.authorized():return self.reply(401,{'error':'Unauthorized'})
   with db() as c:
    messages=[dict(x) for x in c.execute('SELECT id,name,message,status,created_at FROM respect_messages ORDER BY id DESC LIMIT 300')]
    submissions=[dict(x) for x in c.execute('SELECT id,category,name,email,city,role,interest,message,created_at FROM submissions ORDER BY id DESC LIMIT 300')]
   return self.reply(200,{'messages':messages,'submissions':submissions})
  if path.startswith('/api/'):return self.reply(404,{'error':'Not found'})
  if path in ('/server.py','/driver_dignity.db','/saferoad.db','/.env') or path.endswith(('.db','.sqlite','.py','.pyc')):return self.send_error(404)
  return super().do_GET()
 def do_POST(self):
  path=urlparse(self.path).path
  if path not in ('/api/contact','/api/volunteer','/api/respect','/api/admin/login','/api/admin/logout','/api/admin/moderate'):return self.reply(404,{'error':'Not found'})
  if self.limited():return self.reply(429,{'error':'Too many requests. Try again later.'})
  try:
   d=self.data()
   if path=='/api/admin/login':
    if not ADMIN_PASSWORD:return self.reply(503,{'error':'Set ADMIN_PASSWORD on the server first.'})
    if not compare_digest(str(d.get('password','')),ADMIN_PASSWORD):return self.reply(401,{'error':'Invalid password'})
    token=secrets.token_urlsafe(36)
    with LOCK:SESSIONS[token]=time.time()+8*3600
    return self.reply(200,{'success':True},f'dd_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'+('; Secure' if os.environ.get('COOKIE_SECURE')=='1' else ''))
   if path=='/api/admin/logout':
    cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''));t=cookie.get('dd_session')
    with LOCK:
     if t:SESSIONS.pop(t.value,None)
    return self.reply(200,{'success':True},'dd_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
   if path=='/api/admin/moderate':
    if not self.authorized():return self.reply(401,{'error':'Unauthorized'})
    mid=int(d.get('id',0));status=d.get('status')
    if mid<1 or status not in ('approved','rejected','pending'):return self.reply(400,{'error':'Invalid moderation action'})
    with db() as c:cur=c.execute('UPDATE respect_messages SET status=? WHERE id=?',(status,mid))
    return self.reply(200 if cur.rowcount else 404,{'success':bool(cur.rowcount)})
   if path=='/api/respect':
    name=str(d.get('name','')).strip()[:60] or 'A grateful traveller';msg=str(d.get('message','')).strip()
    if not 5<=len(msg)<=500 or len(name)>60:return self.reply(400,{'error':'Enter a message between 5 and 500 characters.'})
    with db() as c:c.execute('INSERT INTO respect_messages(name,message,status,created_at) VALUES(?,?,?,?)',(name,msg,'pending',now()))
    notify('Driver Dignity: new Respect Wall message','A new appreciation message is awaiting moderation in the admin dashboard.')
    return self.reply(201,{'success':True,'message':'Awaiting moderation'})
   cat='volunteer' if path=='/api/volunteer' else 'contact'
   f={k:str(d.get(k,'')).strip() for k in ('name','email','city','role','interest','message')}
   if not 2<=len(f['name'])<=120 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',f['email']) or not 3<=len(f['message'])<=2000:return self.reply(400,{'error':'Please enter a valid name, email and message.'})
   if any(len(f[k])>200 for k in ('email','city','role','interest')) or (cat=='volunteer' and not f['city']):return self.reply(400,{'error':'Check the form fields.'})
   with db() as c:c.execute('INSERT INTO submissions(category,name,email,city,role,interest,message,created_at) VALUES(?,?,?,?,?,?,?,?)',(cat,*(f[k] for k in ('name','email','city','role','interest','message')),now()))
   notify('Driver Dignity: new '+cat,'A new '+cat+' submission is available in the admin dashboard.')
   return self.reply(201,{'success':True,'message':'Thank you! Your submission has been received.'})
  except (ValueError,TypeError,UnicodeDecodeError,json.JSONDecodeError):return self.reply(400,{'error':'Invalid form data.'})
  except Exception as e:print('Request error:',type(e).__name__);return self.reply(500,{'error':'Server error.'})
if __name__=='__main__':
 with db():pass
 print(f'Driver Dignity running at http://localhost:{PORT}')
 if not ADMIN_PASSWORD:print('Admin disabled: set ADMIN_PASSWORD to enable /admin.html')
 ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
