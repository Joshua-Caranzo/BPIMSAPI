from quart import jsonify,request
from functools import wraps
import jwt
from config import SECRET_KEY, CLOUD_NAME, CLOUD_API_KEY, CLOUD_API_SECRET
import hashlib
import re
import cloudinary
import cloudinary.uploader

cloudinary.config( 
    cloud_name = CLOUD_NAME, 
    api_key = CLOUD_API_KEY, 
    api_secret = CLOUD_API_SECRET
)

def create_response(is_success, message, data=None, data2=0, total_count=0):
    return jsonify({
        'isSuccess': is_success,
        'message': message,
        'data': data or [],
        'data2': data2,
        'totalCount': total_count
    })

def token_required(f):
    @wraps(f)
    async def decorator(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization'].split(" ")
            if len(auth_header) > 1:
                token = auth_header[1]

        if not token:
            return jsonify({'message': 'Unauthorized!'}), 401
        
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_id = data.get("sub")
            cart_id = data.get("cartId")

            request.user_id = user_id
            request.cart_id = cart_id if cart_id is not None else None
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401
        
        return await f(*args, **kwargs) 
    
    return decorator


def hash_password_md5(password: str) -> str:
    return hashlib.md5(password.encode('utf-8')).hexdigest()

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*\t\n\r]', '_', filename) 

def upload_media(file_path):
    response = cloudinary.uploader.upload(file_path, resource_type="auto")
    
    return {
        "public_id": response["public_id"], 
        "secure_url": response["secure_url"] 
    }

def delete_media(public_id):
    response = cloudinary.uploader.destroy(public_id, resource_type="image")
    
    return response.get("result") == "ok"