import os
import time
import sqlite3
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

PARTNER_TAG = "lordumungus-20"

# Palavras-chave para busca
KEYWORDS = ["bebe", "bebê", "fraldas", "mamadeira", "carrinho de bebe", "brinquedos bebe"]

# Banco local
DB_PATH = 'produtos.db'
print(f"📁 CRAWLER: Salvando banco em: {DB_PATH}")

def configurar_driver():
    """Configura o Chrome em modo stealth"""
    options = Options()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Descomente se quiser ver o navegador (útil para debug)
    # options.add_argument("--headless=new")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def extrair_preco(produto):
    """Extrai preço de forma robusta"""
    try:
        # Tenta preço inteiro + centavos
        preco_inteiro = produto.find_element(By.CSS_SELECTOR, ".a-price-whole").text
        preco_centavos = produto.find_element(By.CSS_SELECTOR, ".a-price-fraction").text
        inteiro = re.sub(r'[^\d]', '', preco_inteiro)
        centavos = re.sub(r'[^\d]', '', preco_centavos)
        if inteiro and centavos:
            return f"{inteiro},{centavos}"
    except:
        pass
    
    try:
        # Tenta preço completo
        preco_completo = produto.find_element(By.CSS_SELECTOR, ".a-price .a-offscreen").text
        match = re.search(r'[\d.,]+', preco_completo)
        if match:
            return match.group().replace('.', ',')
    except:
        pass
    
    try:
        # Tenta qualquer elemento de preço
        preco_elem = produto.find_element(By.CSS_SELECTOR, ".a-price")
        if preco_elem:
            return "Ver preço"
    except:
        pass
    
    return "Preço indisponível"

def extrair_nome(produto):
    """Extrai nome do produto"""
    try:
        nome_elem = produto.find_element(By.CSS_SELECTOR, "h2 a span")
        return nome_elem.text.strip()
    except:
        try:
            nome_elem = produto.find_element(By.CSS_SELECTOR, "h2")
            return nome_elem.text.strip()
        except:
            return None

def extrair_imagem(produto):
    """Extrai URL da imagem"""
    try:
        img_elem = produto.find_element(By.CSS_SELECTOR, "img.s-image")
        return img_elem.get_attribute("src")
    except:
        return "https://via.placeholder.com/200"

def extrair_link(produto):
    """Extrai link do produto"""
    try:
        link_elem = produto.find_element(By.CSS_SELECTOR, "h2 a")
        link = link_elem.get_attribute("href")
        if link:
            # Limpa o link e adiciona a tag de afiliado
            link = link.split('?')[0]
            link += f"?tag={PARTNER_TAG}"
            return link
    except:
        pass
    return None

def buscar_produtos(driver, keyword):
    print(f"\n🔍 Buscando produtos para: {keyword}")
    
    url = f"https://www.amazon.com.br/s?k={keyword}"
    driver.get(url)
    
    # Aguarda carregar
    time.sleep(3)
    
    # Rola a página para carregar imagens
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    # Encontra todos os produtos
    produtos = driver.find_elements(By.CSS_SELECTOR, "[data-component-type='s-search-result']")
    
    if not produtos:
        produtos = driver.find_elements(By.CSS_SELECTOR, ".s-result-item")
    
    print(f"  📦 Encontrados {len(produtos)} produtos")
    
    resultados = []
    contador = 0
    
    for produto in produtos:
        try:
            # Extrai nome (obrigatório)
            nome = extrair_nome(produto)
            if not nome:
                continue
            
            # Extrai outros campos
            preco = extrair_preco(produto)
            imagem = extrair_imagem(produto)
            link = extrair_link(produto)
            
            if not link:  # Link é obrigatório
                continue
            
            resultados.append((nome, preco, imagem, link))
            contador += 1
            print(f"  ✓ {contador:2d}. {nome[:50]}... - R$ {preco}")
            
        except Exception as e:
            print(f"  ⚠ Erro em um produto: {e}")
            continue
        
        # Pequena pausa entre produtos
        time.sleep(0.5)
        
        # Limite de 20 produtos por keyword
        if len(resultados) >= 20:
            break
    
    return resultados

print("🚀 Iniciando crawler com Selenium...")
driver = configurar_driver()
todos_produtos = []
total_geral = 0

try:
    for keyword in KEYWORDS:
        produtos = buscar_produtos(driver, keyword)
        todos_produtos.extend(produtos)
        total_geral += len(produtos)
        print(f"  → Total parcial: {len(produtos)} produtos para '{keyword}'")
        
        if len(todos_produtos) >= 50:
            print("  🛑 Atingido limite de 50 produtos")
            break
        
        time.sleep(3)
    
    print(f"\n📊 Total de produtos encontrados: {len(todos_produtos)}")
    
    if len(todos_produtos) == 0:
        print("❌ Nenhum produto encontrado!")
        driver.quit()
        exit()
    
    # Salvar no banco
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
    print("🗑️ Banco antigo limpo")
    
    # Insere os novos produtos
    for i, produto in enumerate(todos_produtos[:50], 1):
        cursor.execute("""
        INSERT INTO produtos (nome, preco, imagem, link)
        VALUES (?, ?, ?, ?)
        """, produto)
        if i % 10 == 0:
            print(f"  💾 Salvando... {i} produtos")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ {len(todos_produtos[:50])} produtos salvos com sucesso!")
    
    # Verificação final
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM produtos")
    count = cursor.fetchone()[0]
    conn.close()
    print(f"📊 Verificação: {count} produtos no banco")

finally:
    driver.quit()
    print("👋 Driver encerrado")