import os


def get_var(name):
    try:
        return os.environ(name)
    except KeyError:
        return False


try:
    from secrets import keys as SECRETS
except ImportError:
    SECRETS = {}

DEBUG = get_var("DEBUG")


# if sqlite
if DEBUG:
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
else:
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']

# get secret key for session
SECRET_KEY = SECRETS.get("SECRET_KEY", False) or get_var('SECRET_KEY') or "1234567890"

# flask-toolbar config
DEBUG_TB_INTERCEPT_REDIRECTS = False

# Mail configuration
# Configured in ENV vars
MAIL_SERVER = "smtp.gmail.com"
MAIL_USE_TLS = False
MAIL_USE_SSL = True
MAIL_PORT = 465
MAIL_USERNAME = SECRETS.get("MAIL_USERNAME", False) or get_var('MAIL_USERNAME') or None
MAIL_PASSWORD = SECRETS.get("MAIL_PASSWORD", False) or get_var("MAIL_PASSWORD") or None
MAIL_DEFAULT_SENDER = SECRETS.get("MAIL_DEFAULT_SENDER", False) or get_var("MAIL_DEFAULT_SENDER") or None
MAIL_DEBUG = False
