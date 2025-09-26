import os

SECRET_KEY = '3266a513ac62f8c4be0670900e7fd71342a62f0fc685d900c38985938f49ca39'

SQLALCHEMY_DATABASE_URI = 'sqlite:///project.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = True

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    '..',
    'media', 
    'images'
)
