import requests
import sqlite3
import json
import time
import re
from datetime import datetime

# Configurações
KEYWORDS = ["bebe", "fraldas", "mamadeira"]
LIMITE_PRODUTOS = 30
DB_PATH = 'produtos.db'

print("=" * 60)
print(f"🟢 CRAWLER AMERICANAS JSON - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 60)

def extrair_json_do_html(html):
    """Tenta extrair dados JSON do HTML"""
    # Procura por padrões de JSON na página
    padroes = [
        r'window\.__PRELOADED_STATE__\s*=\s*({.+?});',
        r'__INITIAL_STATE__\s*=\s*({.+?});',
        r'dataLayer\s*=\s*(\[.+?\]);',
        r'var\s+products\s*=\s*(\[.+?\]);'
    ]
    
    for padrao in padroes:
        match = re.search(padrao, html, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                continue
    return None

def buscar_americanas_json(keyword):
    """Busca produtos tentando extrair JSON do HTML"""
    url = f"https://www.americanas.com.br/busca/{keyword}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # Tenta extrair JSON
        dados_json = extrair_json_do_html(response.text)
        
        produtos = []
        
        if dados_json:
            # Navega pelo JSON tentando encontrar produtos
            def encontrar_produtos(obj, caminho=""):
                if isinstance(obj, dict):
                    # Verifica se este objeto parece um produto
                    if obj.get('name') and obj.get('price'):
                        produtos.append({
                            'nome': obj.get('name', ''),
                            'preco': str(obj.get('price', 'Preço indisponível')),
                            'imagem': obj.get('image', obj.get('images', [''])[0] if isinstance(obj.get('images'), list) else ''),
                            'link': f"https://www.americanas.com.br/produto/{obj.get('id', '')}"
                        })
                    
                    # Continua procurando
                    for chave, valor in obj.items():
                        encontrar_produtos(valor, f"{caminho}.{chave}")
                        
                elif isinstance(obj, list):
                    for item in obj:
                        encontrar_produtos(item, f"{caminho}[]")
            
            encontrar_produtos(dados_json)
        
        # Se não encontrou via JSON, tenta método simples
        if not produtos:
            # Procura por padrões simples
            import re
            matches = re.findall(r'<a[^>]*href="([^"]*produto[^"]*)"[^>]*>.*?<[^>]*>(.*?)</a>', response.text, re.DOTALL)
            
            for link, texto in matches[:10]:
                nome = re.sub(r'<[^>]+>', '', texto)
                nome = re.sub(r'\s+', ' ', nome).strip()
                
                if nome and len(nome) > 10:
                    if link.startswith('/'):
                        link = 'https://www.americanas.com.br' + link
                    
                    produtos.append({
                        'nome': nome[:200],
                        'preco': "Preço indisponível",
                        'imagem': "https://via.placeholder.com/200x200?text=Americanas",
                        'link': link
                    })
        
        return produtos[:10]
        
    except Exception as e:
        print(f"  ⚠ Erro: {e}")
        return []

def main():
    todos_produtos = []
    
    for keyword in KEYWORDS:
        print(f"\n🔎 Buscando: {keyword}")
        produtos = buscar_americanas_json(keyword)
        
        if produtos:
            print(f"  ✅ Encontrados {len(produtos)} produtos")
            todos_produtos.extend(produtos)
            
            for p in produtos[:3]:
                print(f"     • {p['nome'][:50]}...")
        
        time.sleep(2)
    
    if todos_produtos:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for p in todos_produtos:
            cursor.execute("""
            INSERT INTO produtos (nome, preco, imagem, link)
            VALUES (?, ?, ?, ?)
            """, (p['nome'], p['preco'], p['imagem'], p['link']))
        
        conn.commit()
        conn.close()
        print(f"\n✅ {len(todos_produtos)} produtos salvos!")
    else:
        print("\n❌ Nenhum produto encontrado")

if __name__ == "__main__":
    main()