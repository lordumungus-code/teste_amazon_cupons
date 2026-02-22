import os
import sqlite3
from flask import Flask, render_template, request
import math
import shutil

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Função para copiar banco do repositório para o volume
def copiar_banco_para_volume():
    if 'RAILWAY_VOLUME_MOUNT_PATH' in os.environ:
        origem = os.path.join(BASE_DIR, 'produtos.db')
        destino = os.path.join(os.environ['RAILWAY_VOLUME_MOUNT_PATH'], 'produtos.db')
        
        # Se existe banco no repositório e NÃO existe no volume
        if os.path.exists(origem) and not os.path.exists(destino):
            shutil.copy2(origem, destino)
            print(f"📋 Banco copiado do repositório para o volume: {destino}")
            return destino
        elif os.path.exists(destino):
            print(f"✅ Usando banco existente no volume: {destino}")
            return destino
    
    return None

# Determina o caminho do banco
if 'RAILWAY_VOLUME_MOUNT_PATH' in os.environ:
    # No Railway: usa o volume
    DB_PATH = os.path.join(os.environ['RAILWAY_VOLUME_MOUNT_PATH'], 'produtos.db')
    
    # Se não existe no volume, tenta copiar do repositório
    if not os.path.exists(DB_PATH):
        banco_copiado = copiar_banco_para_volume()
        if not banco_copiado and os.path.exists('produtos.db'):
            shutil.copy2('produtos.db', DB_PATH)
            print(f"📋 Banco copiado do repositório para: {DB_PATH}")
else:
    # Local: usa o banco da pasta atual
    DB_PATH = 'produtos.db'

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
    info.append("📂 Arquivos no volume (se existir):")
    if 'RAILWAY_VOLUME_MOUNT_PATH' in os.environ:
        volume_path = os.environ['RAILWAY_VOLUME_MOUNT_PATH']
        if os.path.exists(volume_path):
            for f in os.listdir(volume_path):
                full_path = os.path.join(volume_path, f)
                if os.path.isfile(full_path):
                    size = os.path.getsize(full_path)
                    info.append(f"  - {f} ({size} bytes)")
    
    if os.path.exists(DB_PATH):
        size = os.path.getsize(DB_PATH)
        info.append(f"✅ Banco existe! Tamanho: {size} bytes")
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM produtos")
            count = cursor.fetchone()[0]
            info.append(f"📊 Produtos: {count}")
            
            if count > 0:
                cursor.execute("SELECT nome, preco FROM produtos LIMIT 2")
                for nome, preco in cursor.fetchall():
                    info.append(f"  Ex: {nome[:30]}... R$ {preco}")
            conn.close()
        except Exception as e:
            info.append(f"❌ Erro ao ler banco: {e}")
    else:
        info.append("❌ Banco NÃO existe")
    
    return "<br>".join(info)

if __name__ == "__main__":
    app.run(debug=True)