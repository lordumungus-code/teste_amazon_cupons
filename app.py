from flask import Flask, render_template, request
import sqlite3
import os
import math

app = Flask(__name__)

# Usa o caminho do volume se existir, senão usa local
if 'RAILWAY_VOLUME_MOUNT_PATH' in os.environ:
    DB_PATH = os.path.join(os.environ['RAILWAY_VOLUME_MOUNT_PATH'], 'produtos.db')
else:
    DB_PATH = 'produtos.db'  # caminho local para desenvolvimento

PRODUTOS_POR_PAGINA = 12

@app.route("/")
def index():
    pagina = request.args.get('pagina', 1, type=int)
    offset = (pagina - 1) * PRODUTOS_POR_PAGINA
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Garante que a tabela existe
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            preco TEXT,
            imagem TEXT,
            link TEXT
        )
        """)
        
        cursor.execute("SELECT COUNT(*) FROM produtos")
        total_produtos = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT nome, preco, imagem, link 
            FROM produtos 
            ORDER BY id 
            LIMIT ? OFFSET ?
        """, (PRODUTOS_POR_PAGINA, offset))
        
        produtos = cursor.fetchall()
        conn.close()
        
        total_paginas = math.ceil(total_produtos / PRODUTOS_POR_PAGINA)
        
        return render_template("index.html", 
                             produtos=produtos,
                             pagina_atual=pagina,
                             total_paginas=total_paginas,
                             total_produtos=total_produtos)
    
    except Exception as e:
        return f"Erro: {e}"

if __name__ == "__main__":
    app.run(debug=True)