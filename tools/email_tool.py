import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SENDER_EMAIL = os.getenv("EMAIL_ADDRESS")
SENDER_PASSWORD = os.getenv("EMAIL_PASSWORD")


def send_email(to_email: str, subject: str, message: str):
    """
    Sends an email using Gmail SMTP.

    Parameters
    ----------
    to_email : str
        Receiver's email address.

    subject : str
        Email subject.

    message : str
        Email body.

    Returns
    -------
    dict
        {
            "success": bool,
            "message": str
        }
    """

    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return {
            "success": False,
            "message": "Email credentials not found. Check your .env file."
        }

    msg = MIMEText(message)

    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    try:

        server = smtplib.SMTP("smtp.gmail.com", 587)

        server.starttls()

        server.login(
            SENDER_EMAIL,
            SENDER_PASSWORD
        )

        server.send_message(msg)

        server.quit()

        return {
            "success": True,
            "message": "Email sent successfully."
        }

    except Exception as e:

        return {
            "success": False,
            "message": f"Failed to send email: {str(e)}"
        }


if __name__ == "__main__":

    result = send_email(

        "receiver@gmail.com",

        "Test Email",

        "Hello! This is a test email from the AI Research Matching Chatbot."

    )

    print(result)