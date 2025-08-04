import time
import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from . import config

# This scheme will look for a token in the Authorization header, e.g., "Bearer <token>"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Cache for Google's public keys to avoid fetching them on every request
_public_keys_cache = {}

def get_public_keys():
    """
    Fetches Google's public keys for verifying Firebase ID tokens.
    Caches the keys to improve performance.
    """
    global _public_keys_cache
    if not _public_keys_cache or _public_keys_cache.get("expires", 0) < time.time():
        try:
            response = requests.get("https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com")
            response.raise_for_status()
            keys = response.json()
            # The 'expires' time is in the Cache-Control header, e.g., "max-age=21088"
            max_age = int(response.headers['Cache-Control'].split('=')[1])
            keys['expires'] = time.time() + max_age
            _public_keys_cache = keys
        except requests.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not fetch Google's public keys: {e}",
            )
    return _public_keys_cache

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Dependency to verify the Firebase ID token and return the user's data.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        unverified_header = jwt.get_unverified_header(token)
        public_keys = get_public_keys()

        if unverified_header["kid"] not in public_keys:
            raise credentials_exception

        key = public_keys[unverified_header["kid"]]

        payload = jwt.decode(
            token,
            key,
            algorithms=config.ALGORITHMS,
            audience=config.FIREBASE_PROJECT_ID,
            issuer=f"https://securetoken.google.com/{config.FIREBASE_PROJECT_ID}",
        )
        return payload
    except JWTError:
        raise credentials_exception
    except Exception as e:
        print(f"An unexpected error occurred during token validation: {e}")
        raise credentials_exception
