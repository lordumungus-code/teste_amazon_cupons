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

def contar_produtos(caminho):
    """Conta quantos produtos tem em um banco"""
    try:
        conn = sqlite3.connect(caminho)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM produtos")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def get_db_path():
    """Decide qual banco de dados usar - PRIORIDADE PARA O REPOSITÓRIO"""
    
    print("\n" + "="*50)
    print("🔍 VERIFICANDO BANCOS DE DADOS")
    print("="*50)
    
    # Verifica banco do repositório
    if os.path.exists(BANCO_REPOSITORIO):
        count_repositorio = contar_produtos(BANCO_REPOSITORIO)
        print(f"📦 REPOSITÓRIO: {BANCO_REPOSITORIO}")
        print(f"   → {count_repositorio} produtos")
    else:
        count_repositorio = 0
        print(f"❌ REPOSITÓRIO: {BANCO_REPOSITORIO} (não existe)")
    
    # Verifica banco do volume
    if BANCO_VOLUME and os.path.exists(BANCO_VOLUME):
        count_volume = contar_produtos(BANCO_VOLUME)
        print(f"💾 VOLUME: {BANCO_VOLUME}")
        print(f"   → {count_volume} produtos")
    else:
        count_volume = 0
        print(f"❌ VOLUME: {BANCO_VOLUME} (não existe)")
    
    print("-"*50)
    
    # DECISÃO: Priorizar o banco do repositório
    if os.path.exists(BANCO_REPOSITORIO):
        print(f"✅ ESCOLHIDO: REPOSITÓRIO ({count_repositorio} produtos)")
        print("="*50 + "\n")
        return BANCO_REPOSITORIO
    elif BANCO_VOLUME and os.path.exists(BANCO_VOLUME):
        print(f"✅ ESCOLHIDO: VOLUME ({count_volume} produtos)")
        print("="*50 + "\n")
        return BANCO_VOLUME
    else:
        print("❌ NENHUM BANCO ENCONTRADO!")
        print("="*50 + "\n")
        return BANCO_REPOSITORIO

# Força usar o banco do repositório (solução alternativa)
# BANCO_REPOSITORIO_TEMP = os.path.join(BASE_DIR, 'produtos.db')
# if os.path.exists(BANCO_REPOSITORIO_TEMP):
#     DB_PATH = BANCO_REPOSITORIO_TEMP
# else:
#     DB_PATH = get_db_path()

DB_PATH = get_db_path()
count_final = contar_produtos(DB_PATH)
print(f"✅ BANCO EM USO: {DB_PATH} com {count_final} produtos")
print()

PRODUTOS_POR_PAGINA = 12

@app.route("/")
def index():
    pagina = request.args.get('pagina', 1, type=int)
    offset = (pagina - 1) * PRODUTOS_POR_PAGINA
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='produtos'")
        if not cursor.fetchone():
            return "Tabela 'produtos' não encontrada. Execute o crawler primeiro!"
        
        cursor.execute("SELECT COUNT(*) FROM produtos")
        total_produtos = cursor.fetchone()[0]
        
        if total_produtos == 0:
            return render_template("index.html", produtos=None, total_produtos=0)
        
        # Consulta SEM a coluna loja (apenas 4 campos)
        cursor.execute("""
            SELECT nome, preco, imagem, link 
            FROM produtos 
            ORDER BY id DESC 
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
        count = contar_produtos(BANCO_REPOSITORIO)
        info.append(f"  ✅ Existe: {size} bytes, {count} produtos")
    else:
        info.append("  ❌ Não existe")
    
    info.append("")
    info.append("📂 BANCO DO VOLUME:")
    if BANCO_VOLUME and os.path.exists(BANCO_VOLUME):
        size = os.path.getsize(BANCO_VOLUME)
        count = contar_produtos(BANCO_VOLUME)
        info.append(f"  ✅ Existe: {size} bytes, {count} produtos")
    else:
        info.append("  ❌ Não existe")
    
    info.append("")
    info.append(f"✅ BANCO EM USO: {DB_PATH}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(produtos)")
        colunas = cursor.fetchall()
        info.append("")
        info.append("📋 Estrutura da tabela 'produtos':")
        for col in colunas:
            info.append(f"  - {col[1]} ({col[2]})")
        
        cursor.execute("SELECT COUNT(*) FROM produtos")
        total = cursor.fetchone()[0]
        info.append(f"")
        info.append(f"📊 Total de produtos no banco: {total}")
        
        if total > 0:
            cursor.execute("SELECT nome, preco FROM produtos LIMIT 5")
            primeiros = cursor.fetchall()
            info.append("")
            info.append("🔍 Primeiros 5 produtos:")
            for i, p in enumerate(primeiros, 1):
                info.append(f"  {i}. {p[0][:50]}... - R$ {p[1]}")
        
        conn.close()
    except Exception as e:
        info.append(f"Erro ao inspecionar banco: {e}")
    
    return "<pre>" + "<br>".join(info) + "</pre>"

@app.route("/verificar")
def verificar_banco():
    """Rota para verificar o banco de dados"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        html = "<h1>🔍 Diagnóstico do Banco de Dados</h1>"
        html += f"<p><strong>Banco em uso:</strong> {DB_PATH}</p>"
        
        cursor.execute("PRAGMA table_info(produtos)")
        colunas = cursor.fetchall()
        
        html += "<h2>📋 Estrutura da Tabela</h2>"
        html += "<table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse;'>"
        html += "<tr style='background: #f0f0f0;'><th>Coluna</th><th>Tipo</th><th>Permite NULL</th></tr>"
        for col in colunas:
            html += f"<tr><td>{col[1]}</td><td>{col[2]}</td><td>{'SIM' if col[3] else 'NÃO'}</td></tr>"
        html += "</table>"
        
        cursor.execute("SELECT COUNT(*) FROM produtos")
        total = cursor.fetchone()[0]
        html += f"<h2>📦 Total de produtos: <strong>{total}</strong></h2>"
        
        cursor.execute("SELECT id, nome, preco FROM produtos ORDER BY id DESC LIMIT 10")
        ultimos = cursor.fetchall()
        
        html += "<h2>🆕 Últimos 10 Produtos</h2>"
        html += "<table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse; width: 100%;'>"
        html += "<tr style='background: #f0f0f0;'><th>ID</th><th>Nome</th><th>Preço</th></tr>"
        for p in ultimos:
            html += f"<tr><td>{p[0]}</td><td>{p[1][:60]}...</td><td>R$ {p[2]}</td></tr>"
        html += "</table>"
        
        conn.close()
        
        html += "<br><a href='/' style='display: inline-block; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px;'>← Voltar para a página inicial</a>"
        
        return html
    except Exception as e:
        return f"<h1>Erro</h1><p>{e}</p>"

@app.route("/forcar-repositorio")
def forcar_repositorio():
    """Força o uso do banco do repositório"""
    global DB_PATH
    if os.path.exists(BANCO_REPOSITORIO):
        DB_PATH = BANCO_REPOSITORIO
        count = contar_produtos(DB_PATH)
        return f"✅ Banco alterado para REPOSITÓRIO: {DB_PATH} com {count} produtos<br><br><a href='/'>Voltar</a>"
    else:
        return f"❌ Banco do repositório não encontrado!"

@app.route("/forcar-volume")
def forcar_volume():
    """Força o uso do banco do volume"""
    global DB_PATH
    if BANCO_VOLUME and os.path.exists(BANCO_VOLUME):
        DB_PATH = BANCO_VOLUME
        count = contar_produtos(DB_PATH)
        return f"✅ Banco alterado para VOLUME: {DB_PATH} com {count} produtos<br><br><a href='/'>Voltar</a>"
    else:
        return f"❌ Banco do volume não encontrado!"

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))