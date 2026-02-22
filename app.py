import os
import sqlite3
from flask import Flask, render_template, request
import math

app = Flask(__name__)

# CORREÇÃO: Usar caminho ABSOLUTO com base no diretório do app
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'produtos.db')

# Se estiver usando volume do Railway
if 'RAILWAY_VOLUME_MOUNT_PATH' in os.environ:
    DB_PATH = os.path.join(os.environ['RAILWAY_VOLUME_MOUNT_PATH'], 'produtos.db')

print(f"📁 Procurando banco em: {DB_PATH}")  # Isso aparece nos logs

PRODUTOS_POR_PAGINA = 12

@app.route("/")
def index():
    pagina = request.args.get('pagina', 1, type=int)
    offset = (pagina - 1) * PRODUTOS_POR_PAGINA
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verifica se tabela existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='produtos'")
        if not cursor.fetchone():
            return "Tabela 'produtos' não encontrada. Execute o crawler primeiro!"
        
        cursor.execute("SELECT COUNT(*) FROM produtos")
        total_produtos = cursor.fetchone()[0]
        
        if total_produtos == 0:
            return "Nenhum produto encontrado. Execute o crawler primeiro!"
        
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
    
    except sqlite3.Error as e:
        return f"Erro no banco de dados: {e}"
    except Exception as e:
        return f"Erro: {e}"

# Rota de diagnóstico (temporária)
@app.route("/debug")
def debug():
    info = []
    info.append(f"BASE_DIR: {BASE_DIR}")
    info.append(f"DB_PATH: {DB_PATH}")
    info.append(f"Arquivos: {os.listdir(BASE_DIR)}")
    
    if os.path.exists(DB_PATH):
        info.append("✅ Banco existe!")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM produtos")
        count = cursor.fetchone()[0]
        info.append(f"Produtos: {count}")
        conn.close()
    else:
        info.append("❌ Banco NÃO existe")
    
    return "<br>".join(info)

if __name__ == "__main__":
    app.run(debug=True)