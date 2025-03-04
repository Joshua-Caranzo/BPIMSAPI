import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from quart import jsonify
from config import SMTP_SERVER, SMTP_PORT, GMAIL_APP_PASSWORD, GMAIL_SENDER_NAME

def send_email(recipient_email, subject, message):
    if not recipient_email:
        return "No email provided", 400
    
    smtp_server = SMTP_SERVER
    smtp_port = SMTP_PORT
    sender_email = GMAIL_SENDER_NAME
    app_password = GMAIL_APP_PASSWORD

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    
    body = message
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        
        return jsonify({
            'isSuccess': True,
            'message': 'Email successfuly sent',
            'data': None,
            'data2': None,
            'totalCount': None
        }), 200
    
    except Exception as e:
        return f"Failed to send email: {str(e)}", 500