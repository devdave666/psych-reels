import smtplib
import ssl
import sys
from email.mime.text import MIMEText

def send_email(to_addr, from_addr, app_password, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr

    context = ssl.create_default_context()
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls(context=context)
        server.login(from_addr, app_password)
        server.sendmail(from_addr, to_addr, msg.as_string())
    print(f"Email sent: {subject}")

if __name__ == "__main__":
    import os
    to_addr = os.environ['REMINDER_EMAIL_TO']
    from_addr = os.environ['REMINDER_EMAIL_FROM']
    app_password = os.environ['GMAIL_APP_PASSWORD']
    subject = sys.argv[1]
    with open(sys.argv[2]) as f:
        body = f.read()
    send_email(to_addr, from_addr, app_password, subject, body)
