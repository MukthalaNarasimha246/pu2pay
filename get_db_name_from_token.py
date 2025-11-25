from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Query, Request
from jose import jwt
import psycopg2


SECRET_KEY = "51008db3e2713358e71d30334b429a6ccd66e52b93e57e5ba5d7d092c3d4d2e7"
ALGORITHM = "HS256"

# ✅ Extract db_name from JWT
def get_db_name_from_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")[7:]
    print(auth_header,'auth headet')
    # print("Authorization Header:", auth_header)
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYl9uYW1lIjoiREIwMDE1In0.9Wdc8Pia65SGQLIpIwyGRml99hK5zy3S9mxzIZqFtWQ'
    try:
        payload = jwt.decode(auth_header, SECRET_KEY, algorithms=[ALGORITHM])
        db_name = payload.get("db_name")
        if not db_name:
            raise ValueError("Missing db_name in token")
        return db_name
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")



# ✅ Extract db_name from JWT
def get_db_name_from_token_role_based(request):
 
    
    token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYl9uYW1lIjoiREIwMDE1In0.9Wdc8Pia65SGQLIpIwyGRml99hK5zy3S9mxzIZqFtWQ'
    try:
        payload = jwt.decode(request, SECRET_KEY, algorithms=[ALGORITHM])
        db_name = payload.get("db_name")
        if not db_name:
            raise ValueError("Missing db_name in token")
        return db_name
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    
# ✅ Use psycopg2 to connect dynamically
def get_psycopg2_connection(db_name: str):
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user="postgres",
            password="root",
            host="postgres-service",
            port="5432",
            cursor_factory=RealDictCursor  # ⬅️ Converts rows to dict automatically
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection failed: {str(e)}")

# @app.get("/students")
# def get_students(request: Request):
#     db_name = get_db_name_from_token(request)
#     try:
#         conn = get_psycopg2_connection(db_name)
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM image_classification_hypotus")
#         rows = cursor.fetchall()
#         cursor.close()
#         conn.close()
#         return rows  # Already list of dicts via RealDictCursor
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# ✅ Extract db_name from JWT
def get_db_name_from_token_role_based(request):
 
   
    token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYl9uYW1lIjoiREIwMDE1In0.9Wdc8Pia65SGQLIpIwyGRml99hK5zy3S9mxzIZqFtWQ'
    try:
        payload = jwt.decode(request, SECRET_KEY, algorithms=[ALGORITHM])
        db_name = payload.get("db_name")
        if not db_name:
            raise ValueError("Missing db_name in token")
        return db_name
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")