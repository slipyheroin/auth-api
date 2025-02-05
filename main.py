import uvicorn
import os  # Impor os untuk mengambil variabel lingkungan
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from utils import global_exception_handler, validation_exception_handler
from database import Base, engine
from routes import auth, search_ingredients, product

# Inisialisasi aplikasi FastAPI
app = FastAPI()

# Membuat tabel jika belum ada
Base.metadata.create_all(bind=engine)

# Menyertakan router dari modul lain
app.include_router(auth.router)
app.include_router(search_ingredients.router)
app.include_router(product.router)

# Menambahkan penanganan error kustom
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

@app.get("/")
def read_root():
    return {"message": "Hello from Cloud Run"}

if __name__ == "__main__":
    server_port = int(os.environ.get('PORT', 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=server_port, log_level="info")