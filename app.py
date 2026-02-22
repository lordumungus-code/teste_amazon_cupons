import os
import sqlite3
from flask import Flask, render_template, request
import math
import shutil

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Caminhos dos bancos
BANCO_REPOSITORIO = os.path.join(BASE_DIR, 'produtos.db')
BANCO_VOLUME = None

if 'RAILWAY_VOLUME_MOUNT_PATH' in os.environ:
    BANCO_VOLUME = os.path.join(os.environ['RAILWAY_VOLUME_MOUNT_PATH'], 'produtos.db')

# DECISÃO: qual banco usar?
if BANCO_VOLUME and os.path.exists(BANCO_VOLUME):
    # Se existe banco no volume, verifica se tem produtos
    try:
        conn = sqlite3.connect(BANCO_VOLUME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM produtos")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count > 0:
            DB_PATH = BANCO_VOLUME
            print(f"✅ Usando banco do volume com {count} produtos")
        else:
            # Volume vazio, tenta copiar do repositório
            if os.path.exists(BANCO_REPOSITORIO):
                shutil.copy2(BANCO_REPOSITORIO, BANCO_VOLUME)
                DB_PATH = BANCO_VOLUME
                print(f"📋 Banco copiado do repositório para o volume")
            else:
                DB_PATH = BANCO_VOLUME
                print("⚠️ Volume vazio e sem banco no repositório")
    except:
        # Erro ao ler, tenta copiar do repositório
        if os.path.exists(BANCO_REPOSITORIO):
            shutil.copy2(BANCO_REPOSITORIO, BANCO_VOLUME)
            DB_PATH = BANCO_VOLUME
            print(f"📋 Banco copiado do repositório para o volume (após erro)")
        else:
            DB_PATH = BANCO_VOLUME
else:
    # Não tem volume, usa banco do repositório
    DB_PATH = BANCO_REPOSITORIO
    print(f"📁 Usando banco do repositório: {DB_PATH}")

print(f"📁 APP usando banco: {DB_PATH}")

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

@app.route("/debug")
def debug():
    info = []
    info.append(f"BASE_DIR: {BASE_DIR}")
    info.append(f"DB_PATH: {DB_PATH}")
    info.append(f"RAILWAY_VOLUME_MOUNT_PATH: {os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', 'Não definido')}")
    
    info.append("")
    info.append("📂 Arquivos no diretório:")
    for f in os.listdir('.'):
        if os.path.isfile(f):
            size = os.path.getsize(f)
            info.append(f"  - {f} ({size} bytes)")
    
    info.append("")
    info.append("📂 BANCO DO REPOSITÓRIO:")
    if os.path.exists(BANCO_REPOSITORIO):
        size = os.path.getsize(BANCO_REPOSITORIO)
        info.append(f"  ✅ Existe: {size} bytes")
        try:
            conn = sqlite3.connect(BANCO_REPOSITORIO)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM produtos")
            count = cursor.fetchone()[0]
            info.append(f"  📊 Produtos: {count}")
            conn.close()
        except:
            info.append("  ❌ Erro ao ler")
    else:
        info.append("  ❌ Não existe")
    
    info.append("")
    info.append("📂 BANCO DO VOLUME:")
    if BANCO_VOLUME and os.path.exists(BANCO_VOLUME):
        size = os.path.getsize(BANCO_VOLUME)
        info.append(f"  ✅ Existe: {size} bytes")
        try:
            conn = sqlite3.connect(BANCO_VOLUME)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM produtos")
            count = cursor.fetchone()[0]
            info.append(f"  📊 Produtos: {count}")
            conn.close()
        except:
            info.append("  ❌ Erro ao ler")
    else:
        info.append("  ❌ Não existe")
    
    return "<br>".join(info)

if __name__ == "__main__":
    app.run(debug=True)