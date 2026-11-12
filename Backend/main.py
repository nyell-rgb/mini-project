"""
DapurKu - Smart Recipe Finder (Backend)
Jalankan:  uvicorn main:app --reload
Dokumentasi interaktif: http://127.0.0.1:8000/docs
"""
import os
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import bcrypt
import jwt
import mysql.connector
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from db import execute, execute_many, get_db, query

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET", "ganti-secret-ini-di-file-env")
JWT_EXPIRE_HOURS = 12

app = FastAPI(title="DapurKu API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
bearer = HTTPBearer(auto_error=False)


@app.exception_handler(mysql.connector.Error)
async def mysql_error_handler(request: Request, exc: mysql.connector.Error):
    # Detail error hanya dicetak di terminal, tidak dikirim ke klien
    print(f"[MySQL ERROR] {exc}")
    return JSONResponse(status_code=500, content={"detail": "Terjadi kesalahan pada database"})


# ================================================================= Schemas
class RegisterIn(BaseModel):
    nama: str = Field(min_length=1, max_length=100)
    email: str = Field(max_length=100, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=6, max_length=72)


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    nama: str


class IngredientIn(BaseModel):
    nama_bahan: str = Field(min_length=1, max_length=100)
    kategori_bahan: Optional[str] = Field(default=None, max_length=50)


class IngredientOut(BaseModel):
    id_ingredient: int
    nama_bahan: str
    kategori_bahan: Optional[str]


class RecipeIngredientIn(BaseModel):
    id_ingredient: int
    jumlah_kebutuhan: Optional[str] = Field(default=None, max_length=50)


class RecipeIn(BaseModel):
    nama_resep: str = Field(min_length=1, max_length=150)
    waktu_masak: Optional[int] = Field(default=None, ge=0)
    langkah_pembuatan: Optional[str] = None
    ingredients: List[RecipeIngredientIn] = Field(min_length=1)


class RecipeSummary(BaseModel):
    id_recipe: int
    nama_resep: str
    waktu_masak: Optional[int]


class RecipeIngredientOut(BaseModel):
    id_ingredient: int
    nama_bahan: str
    kategori_bahan: Optional[str]
    jumlah_kebutuhan: Optional[str]


class RecipeDetail(BaseModel):
    id_recipe: int
    nama_resep: str
    waktu_masak: Optional[int]
    langkah_pembuatan: Optional[str]
    langkah: List[str]  # langkah sudah dipecah per baris, siap ditampilkan
    bahan: List[RecipeIngredientOut]


class MatchIn(BaseModel):
    ingredient_ids: List[int] = Field(min_length=1)


class MatchOut(BaseModel):
    id_recipe: int
    nama_resep: str
    waktu_masak: Optional[int]
    bahan_cocok: int
    total_bahan: int
    persen_cocok: float
    bahan_kurang: List[str]


# ================================================================= Auth
def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), hashed.encode())
    except ValueError:
        return False


def make_token(user: dict) -> str:
    payload = {
        "sub": str(user["id_user"]),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def current_user(cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
                 conn=Depends(get_db)) -> dict:
    """Dipakai di endpoint yang mengubah data (tambah/edit/hapus)."""
    if not cred:
        raise HTTPException(401, "Harus login dulu")
    try:
        data = jwt.decode(cred.credentials, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Token tidak valid atau sudah kedaluwarsa")
    user = query(conn, "SELECT id_user, nama, email FROM users WHERE id_user=%s",
                 (int(data["sub"]),), one=True)
    if not user:
        raise HTTPException(401, "User tidak ditemukan")
    return user


@app.post("/auth/register", response_model=TokenOut, status_code=201)
def register(data: RegisterIn, conn=Depends(get_db)):
    email = data.email.strip().lower()
    if query(conn, "SELECT 1 FROM users WHERE email=%s", (email,), one=True):
        raise HTTPException(409, "Email sudah terdaftar")
    uid = execute(conn, "INSERT INTO users (nama, email, password) VALUES (%s,%s,%s)",
                  (data.nama.strip(), email, hash_password(data.password)))
    conn.commit()
    return TokenOut(access_token=make_token({"id_user": uid}), nama=data.nama.strip())


@app.post("/auth/login", response_model=TokenOut)
def login(data: LoginIn, conn=Depends(get_db)):
    user = query(conn, "SELECT * FROM users WHERE email=%s",
                 (data.email.strip().lower(),), one=True)
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(401, "Email atau password salah")
    return TokenOut(access_token=make_token(user), nama=user["nama"])


# ================================================================= Root
@app.get("/")
def root():
    return {"app": "DapurKu - Smart Recipe Finder", "docs": "/docs"}


# ================================================================= Ingredients
def rapikan(nama: str) -> str:
    return " ".join(nama.split()).title()  # "bawang  merah" -> "Bawang Merah"


@app.get("/ingredients", response_model=List[IngredientOut])
def list_ingredients(q: Optional[str] = None, kategori: Optional[str] = None,
                     conn=Depends(get_db)):
    sql = "SELECT id_ingredient, nama_bahan, kategori_bahan FROM ingredients WHERE 1=1"
    params = []
    if q:
        sql += " AND nama_bahan LIKE %s"
        params.append(f"%{q.strip()}%")
    if kategori:
        sql += " AND kategori_bahan = %s"
        params.append(kategori)
    sql += " ORDER BY nama_bahan"
    return query(conn, sql, tuple(params))


@app.get("/ingredients/kategori", response_model=List[str])
def list_kategori(conn=Depends(get_db)):
    rows = query(conn, "SELECT DISTINCT kategori_bahan FROM ingredients "
                       "WHERE kategori_bahan IS NOT NULL ORDER BY kategori_bahan")
    return [r["kategori_bahan"] for r in rows]


@app.post("/ingredients", response_model=IngredientOut, status_code=201)
def add_ingredient(data: IngredientIn, conn=Depends(get_db), _=Depends(current_user)):
    nama = rapikan(data.nama_bahan)
    if query(conn, "SELECT 1 FROM ingredients WHERE nama_bahan=%s", (nama,), one=True):
        raise HTTPException(409, "Bahan sudah ada")
    new_id = execute(conn, "INSERT INTO ingredients (nama_bahan, kategori_bahan) VALUES (%s,%s)",
                     (nama, data.kategori_bahan))
    conn.commit()
    return IngredientOut(id_ingredient=new_id, nama_bahan=nama, kategori_bahan=data.kategori_bahan)


@app.put("/ingredients/{id_ingredient}", response_model=IngredientOut)
def edit_ingredient(id_ingredient: int, data: IngredientIn,
                    conn=Depends(get_db), _=Depends(current_user)):
    if not query(conn, "SELECT 1 FROM ingredients WHERE id_ingredient=%s", (id_ingredient,), one=True):
        raise HTTPException(404, "Bahan tidak ditemukan")
    nama = rapikan(data.nama_bahan)
    if query(conn, "SELECT 1 FROM ingredients WHERE nama_bahan=%s AND id_ingredient<>%s",
             (nama, id_ingredient), one=True):
        raise HTTPException(409, "Nama bahan sudah dipakai")
    execute(conn, "UPDATE ingredients SET nama_bahan=%s, kategori_bahan=%s WHERE id_ingredient=%s",
            (nama, data.kategori_bahan, id_ingredient))
    conn.commit()
    return IngredientOut(id_ingredient=id_ingredient, nama_bahan=nama, kategori_bahan=data.kategori_bahan)


@app.delete("/ingredients/{id_ingredient}", status_code=204)
def delete_ingredient(id_ingredient: int, force: bool = False,
                      conn=Depends(get_db), _=Depends(current_user)):
    if not query(conn, "SELECT 1 FROM ingredients WHERE id_ingredient=%s", (id_ingredient,), one=True):
        raise HTTPException(404, "Bahan tidak ditemukan")
    dipakai = query(conn, "SELECT COUNT(*) AS n FROM recipe_ingredients WHERE id_ingredient=%s",
                    (id_ingredient,), one=True)["n"]
    # Di database ada ON DELETE CASCADE: tanpa pengecekan ini bahan akan hilang dari semua resep
    if dipakai and not force:
        raise HTTPException(409, f"Bahan dipakai di {dipakai} resep. Tambahkan ?force=true untuk tetap menghapus")
    execute(conn, "DELETE FROM ingredients WHERE id_ingredient=%s", (id_ingredient,))
    conn.commit()


# ================================================================= Recipes
def split_steps(teks: Optional[str]) -> List[str]:
    if not teks:
        return []
    baris = [b.strip() for b in teks.replace("\\n", "\n").split("\n") if b.strip()]
    return [re.sub(r"^\d+[\.\)]\s*", "", b) for b in baris]  # buang nomor "1. "


def load_recipe(conn, id_recipe: int) -> dict:
    r = query(conn, "SELECT id_recipe, nama_resep, waktu_masak, langkah_pembuatan "
                    "FROM recipes WHERE id_recipe=%s", (id_recipe,), one=True)
    if not r:
        raise HTTPException(404, "Resep tidak ditemukan")
    r["bahan"] = query(conn, """
        SELECT i.id_ingredient, i.nama_bahan, i.kategori_bahan, ri.jumlah_kebutuhan
        FROM recipe_ingredients ri
        JOIN ingredients i ON i.id_ingredient = ri.id_ingredient
        WHERE ri.id_recipe=%s ORDER BY i.nama_bahan""", (id_recipe,))
    r["langkah"] = split_steps(r["langkah_pembuatan"])
    return r


def validate_ingredients(conn, items: List[RecipeIngredientIn]):
    ids = [i.id_ingredient for i in items]
    if len(ids) != len(set(ids)):
        raise HTTPException(400, "Ada bahan yang dimasukkan dua kali")
    marks = ",".join(["%s"] * len(ids))
    ada = {r["id_ingredient"] for r in
           query(conn, f"SELECT id_ingredient FROM ingredients WHERE id_ingredient IN ({marks})", tuple(ids))}
    hilang = sorted(set(ids) - ada)
    if hilang:
        raise HTTPException(400, f"id_ingredient tidak ditemukan: {hilang}")


@app.get("/recipes", response_model=List[RecipeSummary])
def list_recipes(q: Optional[str] = None, skip: int = Query(0, ge=0),
                 limit: int = Query(20, ge=1, le=100), conn=Depends(get_db)):
    sql = "SELECT id_recipe, nama_resep, waktu_masak FROM recipes"
    params: list = []
    if q:
        sql += " WHERE nama_resep LIKE %s"
        params.append(f"%{q.strip()}%")
    sql += " ORDER BY nama_resep LIMIT %s OFFSET %s"
    params += [limit, skip]
    return query(conn, sql, tuple(params))


@app.get("/recipes/{id_recipe}", response_model=RecipeDetail)
def recipe_detail(id_recipe: int, conn=Depends(get_db)):
    return load_recipe(conn, id_recipe)


@app.post("/recipes", response_model=RecipeDetail, status_code=201)
def add_recipe(data: RecipeIn, conn=Depends(get_db), _=Depends(current_user)):
    validate_ingredients(conn, data.ingredients)
    new_id = execute(conn,
                     "INSERT INTO recipes (nama_resep, waktu_masak, langkah_pembuatan) VALUES (%s,%s,%s)",
                     (data.nama_resep.strip(), data.waktu_masak, data.langkah_pembuatan))
    execute_many(conn,
                 "INSERT INTO recipe_ingredients (id_recipe, id_ingredient, jumlah_kebutuhan) VALUES (%s,%s,%s)",
                 [(new_id, i.id_ingredient, i.jumlah_kebutuhan) for i in data.ingredients])
    conn.commit()
    return load_recipe(conn, new_id)


@app.put("/recipes/{id_recipe}", response_model=RecipeDetail)
def edit_recipe(id_recipe: int, data: RecipeIn, conn=Depends(get_db), _=Depends(current_user)):
    load_recipe(conn, id_recipe)  # 404 kalau tidak ada
    validate_ingredients(conn, data.ingredients)
    execute(conn,
            "UPDATE recipes SET nama_resep=%s, waktu_masak=%s, langkah_pembuatan=%s WHERE id_recipe=%s",
            (data.nama_resep.strip(), data.waktu_masak, data.langkah_pembuatan, id_recipe))
    execute(conn, "DELETE FROM recipe_ingredients WHERE id_recipe=%s", (id_recipe,))
    execute_many(conn,
                 "INSERT INTO recipe_ingredients (id_recipe, id_ingredient, jumlah_kebutuhan) VALUES (%s,%s,%s)",
                 [(id_recipe, i.id_ingredient, i.jumlah_kebutuhan) for i in data.ingredients])
    conn.commit()
    return load_recipe(conn, id_recipe)


@app.delete("/recipes/{id_recipe}", status_code=204)
def delete_recipe(id_recipe: int, conn=Depends(get_db), _=Depends(current_user)):
    load_recipe(conn, id_recipe)
    execute(conn, "DELETE FROM recipes WHERE id_recipe=%s", (id_recipe,))  # bahan ikut terhapus (CASCADE)
    conn.commit()


# ================================================================= Fitur utama: pencocokan
@app.post("/match", response_model=List[MatchOut])
def match_recipes(data: MatchIn, min_persen: float = Query(0, ge=0, le=100),
                  conn=Depends(get_db)):
    """Cocokkan bahan yang dimiliki user dengan resep di database."""
    dipilih = set(data.ingredient_ids)
    marks = ",".join(["%s"] * len(dipilih))
    rows = query(conn, f"""
        SELECT r.id_recipe, r.nama_resep, r.waktu_masak, i.id_ingredient, i.nama_bahan
        FROM recipes r
        JOIN recipe_ingredients ri ON ri.id_recipe = r.id_recipe
        JOIN ingredients i ON i.id_ingredient = ri.id_ingredient
        WHERE r.id_recipe IN (
            SELECT id_recipe FROM recipe_ingredients WHERE id_ingredient IN ({marks})
        )""", tuple(dipilih))

    resep = {}
    for row in rows:
        r = resep.setdefault(row["id_recipe"], {
            "id_recipe": row["id_recipe"], "nama_resep": row["nama_resep"],
            "waktu_masak": row["waktu_masak"], "semua": {},
        })
        r["semua"][row["id_ingredient"]] = row["nama_bahan"]

    hasil = []
    for r in resep.values():
        total = len(r["semua"])
        cocok = len(dipilih & r["semua"].keys())
        persen = round(cocok / total * 100, 1)
        if persen < min_persen:
            continue
        hasil.append(MatchOut(
            id_recipe=r["id_recipe"], nama_resep=r["nama_resep"], waktu_masak=r["waktu_masak"],
            bahan_cocok=cocok, total_bahan=total, persen_cocok=persen,
            bahan_kurang=sorted(n for i, n in r["semua"].items() if i not in dipilih),
        ))
    # Paling lengkap dulu, lalu yang paling sedikit kekurangannya
    hasil.sort(key=lambda h: (-h.persen_cocok, len(h.bahan_kurang), h.nama_resep))
    return hasil
