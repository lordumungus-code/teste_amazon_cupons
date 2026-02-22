import os
import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import re

PARTNER_TAG = "lordumungus-20"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Palavras-chave para busca
KEYWORDS = ["bebe", "bebê", "fraldas", "mamadeira", "carrinho de bebe", "brinquedos bebe"]

# Sempre salva localmente (no seu PC)
DB_PATH = 'produtos.db'
print(f"📁 CRAWLER: Salvando banco em: {DB_PATH}")

def extrair_preco_completo(produto):
    """Função para extrair preço com centavos"""
    
    # Tenta encontrar o preço inteiro + centavos
    preco_inteiro = produto.select_one(".a-price-whole")
    preco_centavos = produto.select_one(".a-price-fraction")
    
    if preco_inteiro and preco_centavos:
        # Limpa o texto (remove pontos e caracteres especiais)
        inteiro = re.sub(r'[^\d]', '', preco_inteiro.text)
        centavos = re.sub(r'[^\d]', '', preco_centavos.text)
        
        # Formata o preço completo
        if inteiro and centavos:
            return f"{inteiro},{centavos}"
    
    # Tenta o seletor de preço completo
    preco_completo = produto.select_one(".a-price .a-offscreen")
    if preco_completo:
        preco_texto = preco_completo.text.strip()
        # Extrai apenas números e vírgula/ponto
        match = re.search(r'[\d.,]+', preco_texto)
        if match:
            return match.group().replace('.', ',')
    
    # Tenta outros formatos de preço
    preco_span = produto.select_one("span.a-price[data-a-size='xl'] span.a-offscreen")
    if preco_span:
        return preco_span.text.strip().replace('R$', '').strip()
    
    return "Preço indisponível"

def buscar_produtos(keyword):
    print(f"\n🔍 Buscando produtos para: {keyword}")
    
    URL = f"https://www.amazon.com.br/s?k={keyword}"
    
    try:
        response = requests.get(URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Erro na requisição: {e}")
        return []
    
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Seletores da Amazon
    produtos = soup.select("[data-component-type='s-search-result']")
    
    if not produtos:
        produtos = soup.select(".s-result-item")
    
    resultados = []
    
    for produto in produtos[:20]:
        try:
            # Nome do produto
            nome_elem = produto.select_one("h2 a span") or produto.select_one("h2")
            if not nome_elem:
                continue
            nome = nome_elem.text.strip()
            
            # PREÇO
            preco = extrair_preco_completo(produto)
            
            # Imagem
            img_elem = produto.select_one("img.s-image")
            if img_elem and img_elem.get("src"):
                imagem = img_elem["src"]
            else:
                imagem = ""
            
            # Link
            link_elem = produto.select_one("h2 a") or produto.select_one("a.a-link-normal")
            if link_elem and link_elem.get("href"):
                link = "https://www.amazon.com.br" + link_elem["href"].split('?')[0]
                link += f"?tag={PARTNER_TAG}"
            else:
                continue
            
            resultados.append((nome, preco, imagem, link))
            print(f"  ✓ {nome[:50]}... - R$ {preco}")
            
        except Exception as e:
            print(f"  ⚠ Erro ao processar produto: {e}")
            continue
        
        time.sleep(0.5)
    
    return resultados

# Conecta ao banco de dados LOCAL
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Cria a tabela se não existir
cursor.execute("""
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    preco TEXT,
    imagem TEXT,
    link TEXT
)
""")

# Limpa produtos antigos
cursor.execute("DELETE FROM produtos")

todos_produtos = []

# Busca produtos para cada palavra-chave
for keyword in KEYWORDS:
    produtos = buscar_produtos(keyword)
    todos_produtos.extend(produtos)
    
    if len(todos_produtos) >= 50:
        break
    
    time.sleep(2)

# Insere os produtos no banco de dados
for produto in todos_produtos[:50]:
    cursor.execute("""
    INSERT INTO produtos (nome, preco, imagem, link)
    VALUES (?, ?, ?, ?)
    """, produto)

conn.commit()
conn.close()

print(f"\n✅ {len(todos_produtos[:50])} produtos salvos com sucesso em: {DB_PATH}")
print(f"📊 Total no banco: {len(todos_produtos[:50])} produtos")