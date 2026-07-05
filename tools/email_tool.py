import smtplib
from email.mime.text import MIMEText

def send_email(to_email, subject, message):

    sender_email = "your_email@gmail.com"
    sender_password = "your_app_password"

    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        return "Email sent successfully"

    except Exception as e:
        return f"Email failed: {str(e)}"
