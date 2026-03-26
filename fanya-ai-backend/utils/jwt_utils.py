from flask_jwt_extended import get_jwt_identity
from models.user import User

def get_user_from_token():
    user_id = get_jwt_identity()
    return User.query.get(user_id)