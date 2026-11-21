"""DapurKu API - FastAPI backend untuk database db_dapur."""
import os, re, hashlib, hmac
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import mysql.connector
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import jwt

load_dotenv()
app=FastAPI(title="DapurKu API", version="1.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
JWT_SECRET=os.getenv("JWT_SECRET", "ubah-secret-dapurku-di-env")
JWT_EXP_HOURS=12
ROLE_CREATE={"Chef", "Ibu Rumah Tangga", "Anak Kos"}
ROLE_EDIT={"Chef"}
ROLE_DELETE={"Chef"}

class LoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=255)

class RegisterPayload(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=255)
    role: str = Field(min_length=1, max_length=50)

@app.get("/auth/roles")
def auth_roles():
    """Ambil pilihan role langsung dari definisi kolom users.role di MySQL."""
    col=query("SHOW COLUMNS FROM users LIKE 'role'", one=True)
    if not col or not col.get("Type", "").lower().startswith("enum("):
        raise HTTPException(500, "Kolom users.role tidak ditemukan atau bukan ENUM")
    enum_type=col["Type"]
    values=re.findall(r"'((?:[^'\\]|\\.)*)'", enum_type)
    return [v.replace("\\'", "'").replace("\\\\", "\\") for v in values]

@app.post("/auth/register", status_code=201)
def auth_register(data: RegisterPayload):
    roles=auth_roles()
    if data.role not in roles:
        raise HTTPException(400, "Kategori role tidak valid")
    username=data.username.strip()
    if not username:
        raise HTTPException(400, "Username tidak boleh kosong")
    existing=query("SELECT id_users FROM users WHERE username=%s", (username,), one=True)
    if existing:
        raise HTTPException(409, "Username sudah digunakan")
    hashed=hashlib.sha256(data.password.encode()).hexdigest()
    try:
        uid=write("INSERT INTO users(username,password_hash,role) VALUES(%s,%s,%s)", (username,hashed,data.role))
    except mysql.connector.IntegrityError:
        raise HTTPException(409, "Username sudah digunakan")
    return {"message":"Pendaftaran berhasil", "id_users":uid, "username":username, "role":data.role}

def _verify_password(raw, saved):
    raw_hash=hashlib.sha256(raw.encode()).hexdigest()
    if hmac.compare_digest(raw_hash, str(saved)):
        return True
    # Mendukung password_hash bcrypt bila akun sebelumnya memakai bcrypt.
    try:
        import bcrypt
        return bcrypt.checkpw(raw.encode(), str(saved).encode())
    except Exception:
        return False

def _make_token(user):
    return jwt.encode({"sub": str(user["id_users"]), "exp": datetime.now(timezone.utc)+timedelta(hours=JWT_EXP_HOURS)}, JWT_SECRET, algorithm="HS256")

def _current_user(authorization: Optional[str]=Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Silakan login terlebih dahulu")
    try:
        payload=jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])
        uid=int(payload["sub"])
    except Exception:
        raise HTTPException(401, "Token tidak valid atau kedaluwarsa")
    user=query("SELECT id_users,username,role FROM users WHERE id_users=%s", (uid,), one=True)
    if not user: raise HTTPException(401, "Akun tidak ditemukan")
    return user

def _require_role(allowed, user):
    if user.get("role") not in allowed:
        raise HTTPException(403, "Akses tidak diizinkan untuk role akun ini")
    return user

def connect():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST","localhost"),
        port=int(os.getenv("DB_PORT","3306")),
        user=os.getenv("DB_USER","root"),
        password=os.getenv("DB_PASSWORD",""),
        database=os.getenv("DB_NAME","db_dapur"),
        charset="utf8mb4"
    )

def query(sql, params=(), one=False):
    db=connect()
    try:
        cur=db.cursor(dictionary=True)
        cur.execute(sql,params)
        result=cur.fetchone() if one else cur.fetchall()
        return result
    finally:
        db.close()

def write(sql, params=(), many=None):
    db=connect()
    try:
        cur=db.cursor()
        if many is not None: cur.executemany(sql,many)
        else: cur.execute(sql,params)
        db.commit()
        return cur.lastrowid
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def favorites_table():
    # Tabel recipe_favorites ada pada dump database yang disertakan.
    return True

class IngredientPayload(BaseModel):
    nama_bahan: str = Field(min_length=1,max_length=100)
    kategori_bahan: Optional[str] = None

class RecipeIngredientPayload(BaseModel):
    nama_bahan: str = Field(min_length=1,max_length=100)
    jumlah_kebutuhan: Optional[str] = Field(default=None,max_length=50)

class RecipePayload(BaseModel):
    nama_resep: str = Field(min_length=1,max_length=150)
    waktu_masak: Optional[int] = Field(default=None,ge=0)
    langkah_pembuatan: Optional[str] = None
    foto: Optional[str] = None
    bahan: List[RecipeIngredientPayload] = Field(default_factory=list)

def recipe_detail(recipe_id):
    row=query("""SELECT r.id_recipe,r.nama_resep,r.waktu_masak,r.langkah_pembuatan,r.foto,
        (EXISTS(SELECT 1 FROM recipe_favorites f WHERE f.id_recipe=r.id_recipe)
          OR COALESCE(r.favorit,0)=1) AS favorit
        FROM recipes r WHERE r.id_recipe=%s""",(recipe_id,),one=True)
    if not row: raise HTTPException(404,"Resep tidak ditemukan")
    row["favorit"]=bool(row["favorit"])
    row["bahan"]=query("""SELECT i.id_ingredient,i.nama_bahan,i.kategori_bahan,ri.jumlah_kebutuhan
        FROM recipe_ingredients ri JOIN ingredients i ON i.id_ingredient=ri.id_ingredient
        WHERE ri.id_recipe=%s ORDER BY i.nama_bahan""",(recipe_id,))
    row["langkah"]=[re.sub(r"^\s*\d+[\.)]\s*","",x.strip()) for x in (row["langkah_pembuatan"] or "").splitlines() if x.strip()]
    return row

def save_recipe(payload, recipe_id=None):
    # Pastikan bahan ada; nama bahan dari frontend dihubungkan ke id ingredient.
    db=connect()
    try:
        cur=db.cursor()
        if recipe_id is not None:
            cur.execute("SELECT id_recipe FROM recipes WHERE id_recipe=%s",(recipe_id,))
            if not cur.fetchone(): raise HTTPException(404,"Resep tidak ditemukan")
            cur.execute("UPDATE recipes SET nama_resep=%s,waktu_masak=%s,langkah_pembuatan=%s,foto=%s WHERE id_recipe=%s",
                (payload.nama_resep.strip(),payload.waktu_masak,payload.langkah_pembuatan,payload.foto,recipe_id))
            cur.execute("DELETE FROM recipe_ingredients WHERE id_recipe=%s",(recipe_id,))
            rid=recipe_id
        else:
            cur.execute("SELECT id_recipe FROM recipes WHERE LOWER(nama_resep)=LOWER(%s)",(payload.nama_resep.strip(),))
            if cur.fetchone(): raise HTTPException(409,"Nama resep sudah terdaftar")
            cur.execute("INSERT INTO recipes(nama_resep,waktu_masak,langkah_pembuatan,foto) VALUES(%s,%s,%s,%s)",
                (payload.nama_resep.strip(),payload.waktu_masak,payload.langkah_pembuatan,payload.foto))
            rid=cur.lastrowid
        seen=set()
        for item in payload.bahan:
            name=" ".join(item.nama_bahan.split()).title()
            if not name or name.lower() in seen: continue
            seen.add(name.lower())
            cur.execute("SELECT id_ingredient FROM ingredients WHERE LOWER(nama_bahan)=LOWER(%s)",(name,))
            ing=cur.fetchone()
            if ing: iid=ing[0]
            else:
                cur.execute("INSERT INTO ingredients(nama_bahan) VALUES(%s)",(name,))
                iid=cur.lastrowid
            cur.execute("INSERT INTO recipe_ingredients(id_recipe,id_ingredient,jumlah_kebutuhan) VALUES(%s,%s,%s)",
                (rid,iid,(item.jumlah_kebutuhan or "").strip() or None))
        db.commit()
        return rid
    except Exception:
        db.rollback()
        raise
    finally: db.close()

@app.post("/auth/login")
def auth_login(data: LoginPayload):
    user=query("SELECT id_users,username,password_hash,role FROM users WHERE username=%s", (data.username.strip(),), one=True)
    if not user or not _verify_password(data.password, user["password_hash"]):
        raise HTTPException(401, "Username atau password salah")
    public={"id_users":user["id_users"],"username":user["username"],"role":user["role"]}
    return {"access_token":_make_token(user),"token_type":"bearer","user":public}

@app.get("/auth/me")
def auth_me(user=Depends(_current_user)):
    return user

@app.get("/")
def home(): return {"app":"DapurKu API","database":"db_dapur","status":"ok"}

@app.get("/health")
def health():
    try:
        db=connect()
        db.close()
        return {"status":"connected","database":os.getenv("DB_NAME","db_dapur")}
    except mysql.connector.Error as e:
        raise HTTPException(503,f"Database tidak terhubung: {e}")

@app.get("/ingredients")
def ingredients(q: Optional[str]=None, kategori: Optional[str]=None):
    sql="SELECT id_ingredient,nama_bahan,kategori_bahan FROM ingredients WHERE 1=1"; args=[]
    if q: sql+=" AND nama_bahan LIKE %s"; args.append(f"%{q}%")
    if kategori: sql+=" AND kategori_bahan=%s"; args.append(kategori)
    sql+=" ORDER BY nama_bahan"
    return query(sql,tuple(args))

@app.get("/recipes")
def recipes(q: Optional[str]=None, favorite: Optional[bool]=None):
    sql="""SELECT r.id_recipe,r.nama_resep,r.waktu_masak,r.langkah_pembuatan,r.foto,
        (EXISTS(SELECT 1 FROM recipe_favorites f WHERE f.id_recipe=r.id_recipe)
          OR COALESCE(r.favorit,0)=1) AS favorit
        FROM recipes r WHERE 1=1"""; args=[]
    if q: sql+=" AND r.nama_resep LIKE %s"; args.append(f"%{q}%")
    if favorite is True: sql+=" AND (EXISTS(SELECT 1 FROM recipe_favorites f WHERE f.id_recipe=r.id_recipe) OR COALESCE(r.favorit,0)=1)"
    sql+=" ORDER BY r.id_recipe DESC"
    rows=query(sql,tuple(args))
    for row in rows:
        row["favorit"]=bool(row["favorit"])
        row["bahan"]=query("""SELECT i.nama_bahan,ri.jumlah_kebutuhan FROM recipe_ingredients ri
            JOIN ingredients i ON i.id_ingredient=ri.id_ingredient WHERE ri.id_recipe=%s ORDER BY i.nama_bahan""",(row["id_recipe"],))
        row["langkah"]=[re.sub(r"^\s*\d+[\.)]\s*","",x.strip()) for x in (row["langkah_pembuatan"] or "").splitlines() if x.strip()]
    return rows

@app.get("/recipes/{recipe_id}")
def recipe(recipe_id:int): return recipe_detail(recipe_id)

@app.post("/recipes",status_code=201)
def create_recipe(data:RecipePayload, user=Depends(_current_user)):
    _require_role(ROLE_CREATE, user)
    return recipe_detail(save_recipe(data))

@app.put("/recipes/{recipe_id}")
def update_recipe(recipe_id:int,data:RecipePayload,user=Depends(_current_user)):
    _require_role(ROLE_EDIT, user)
    save_recipe(data,recipe_id)
    return recipe_detail(recipe_id)

@app.delete("/recipes/{recipe_id}",status_code=204)
def delete_recipe(recipe_id:int,user=Depends(_current_user)):
    _require_role(ROLE_DELETE, user)
    if not query("SELECT id_recipe FROM recipes WHERE id_recipe=%s",(recipe_id,),one=True):
        raise HTTPException(404,"Resep tidak ditemukan")
    write("DELETE FROM recipes WHERE id_recipe=%s",(recipe_id,))

@app.put("/recipes/{recipe_id}/favorite")
def set_favorite(recipe_id:int, favorit:bool, user=Depends(_current_user)):
    if not query("SELECT id_recipe FROM recipes WHERE id_recipe=%s",(recipe_id,),one=True):
        raise HTTPException(404,"Resep tidak ditemukan")
    if favorit:
        write("INSERT IGNORE INTO recipe_favorites(id_recipe) VALUES(%s)",(recipe_id,))
    else:
        write("DELETE FROM recipe_favorites WHERE id_recipe=%s",(recipe_id,))
    # Kolom favorit yang ada pada dump juga dijaga sinkron bila tersedia.
    try: write("UPDATE recipes SET favorit=%s WHERE id_recipe=%s",(int(favorit),recipe_id))
    except mysql.connector.Error: pass
    return {"id_recipe":recipe_id,"favorit":favorit}

@app.post("/match")
def match(data:dict):
    ingredient_names=[str(x).strip() for x in data.get("ingredients",[]) if str(x).strip()]
    if not ingredient_names: raise HTTPException(400,"Pilih setidaknya satu bahan")
    ids=[]
    for name in ingredient_names:
        row=query("SELECT id_ingredient FROM ingredients WHERE LOWER(nama_bahan)=LOWER(%s)",(name,),one=True)
        if row: ids.append(row["id_ingredient"])
    if not ids: return []
    marks=",".join(["%s"]*len(ids))
    rows=query(f"""SELECT r.id_recipe,r.nama_resep,r.waktu_masak,i.id_ingredient,i.nama_bahan
        FROM recipes r JOIN recipe_ingredients ri ON ri.id_recipe=r.id_recipe
        JOIN ingredients i ON i.id_ingredient=ri.id_ingredient
        WHERE r.id_recipe IN (SELECT id_recipe FROM recipe_ingredients WHERE id_ingredient IN ({marks}))""",tuple(ids))
    grouped={}
    chosen=set(ids)
    for row in rows:
        x=grouped.setdefault(row["id_recipe"],{"id_recipe":row["id_recipe"],"nama_resep":row["nama_resep"],"waktu_masak":row["waktu_masak"],"ids":set(),"names":{}})
        x["ids"].add(row["id_ingredient"]); x["names"][row["id_ingredient"]]=row["nama_bahan"]
    out=[]
    for x in grouped.values():
        total=len(x["ids"]); got=len(x["ids"]&chosen)
        out.append({"id_recipe":x["id_recipe"],"nama_resep":x["nama_resep"],"waktu_masak":x["waktu_masak"],
          "bahan_cocok":got,"total_bahan":total,"persen_cocok":round(got/total*100,1),
          "bahan_kurang":sorted(n for i,n in x["names"].items() if i not in chosen)})
    return sorted(out,key=lambda x:(-x["persen_cocok"],len(x["bahan_kurang"]),x["nama_resep"]))
