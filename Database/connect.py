import mysql.connector

def create_connection():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="db_dapur"  
        )
        if db.is_connected():
            print("Berhasil terhubung ke database db_dapur!")
            return db
    except mysql.connector.Error as err:
        print(f"Koneksi gagal: {err}")
        return None

if __name__ == "__main__":
    create_connection()