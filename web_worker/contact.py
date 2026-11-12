"""Configured opt-in signup with durable throttling; no mail during UI previews."""
from email.message import EmailMessage
import os
import re
import smtplib
import ssl
import sqlite3
import time
from sma_analyzer.notifications import validate_email

def enabled():
    return all(os.environ.get(key) for key in ('SMTP_HOST','SMTP_USER','SMTP_PASSWORD','CONTACT_FROM','CONTACT_TO'))

def send(directory, body):
    if not enabled(): raise ValueError('Release updates are not configured yet.')
    email=str(body.get('email','')).strip()
    identifier=str(body.get('install_id',''))
    if len(email)>254 or not validate_email(email): raise ValueError('Enter a valid email address.')
    if not re.fullmatch(r'[a-zA-Z0-9-]{16,64}',identifier): raise ValueError('Invalid installation identifier.')
    with sqlite3.connect(str(directory/'contact.sqlite3')) as db:
        db.execute('CREATE TABLE IF NOT EXISTS contact_rate (id TEXT PRIMARY KEY, at REAL NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        recent=db.execute('SELECT COUNT(*) FROM contact_rate WHERE at>?',(time.time()-3600,)).fetchone()[0]
        previous=db.execute('SELECT at FROM contact_rate WHERE id=?',(identifier,)).fetchone()
        if recent>=20 or previous and time.time()-previous[0]<300:
            raise ValueError('Please wait before submitting another signup.')
        db.execute('INSERT INTO contact_rate VALUES (?,?) ON CONFLICT(id) DO UPDATE SET at=excluded.at',(identifier,time.time()))
    message=EmailMessage()
    message['Subject']='SMA release-update signup'
    message['From']=os.environ['CONTACT_FROM'];message['To']=os.environ['CONTACT_TO']
    message.set_content(f'A user opted into release updates.\nEmail: {email}\nInstallation: {identifier}\n')
    with smtplib.SMTP(os.environ['SMTP_HOST'],int(os.environ.get('SMTP_PORT','587')),timeout=15) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD']);smtp.send_message(message)
    return {'sent':True}
