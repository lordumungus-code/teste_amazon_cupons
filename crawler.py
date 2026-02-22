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
    
    # Executa em segundo plano (mais rápido)
    options.add_argument("--headless=new")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    # Remove a flag de automação
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def extrair_preco_completo(produto):
    """Extrai preço dos elementos"""
    try:
        # Tenta o preço inteiro
        preco_inteiro = produto.find_element(By.CSS_SELECTOR, ".a-price-whole").text
        preco_centavos = produto.find_element(By.CSS_SELECTOR, ".a-price-fraction").text
        
        inteiro = re.sub(r'[^\d]', '', preco_inteiro)
        centavos = re.sub(r'[^\d]', '', preco_centavos)
        
        if inteiro and centavos:
            return f"{inteiro},{centavos}"
    except:
        pass
    
    try:
        preco_completo = produto.find_element(By.CSS_SELECTOR, ".a-price .a-offscreen").text
        match = re.search(r'[\d.,]+', preco_completo)
        if match:
            return match.group().replace('.', ',')
    except:
        pass
    
    return "Preço indisponível"

def buscar_produtos(driver, keyword):
    print(f"\n🔍 Buscando produtos para: {keyword}")
    
    url = f"https://www.amazon.com.br/s?k={keyword}"
    driver.get(url)
    
    # Aguarda carregar
    time.sleep(3)
    
    # Rola a página para carregar tudo
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    produtos = driver.find_elements(By.CSS_SELECTOR, "[data-component-type='s-search-result']")
    
    if not produtos:
        produtos = driver.find_elements(By.CSS_SELECTOR, ".s-result-item")
    
    print(f"  📦 Encontrados {len(produtos)} produtos")
    
    resultados = []
    
    for produto in produtos[:20]:
        try:
            # Nome
            nome_elem = produto.find_element(By.CSS_SELECTOR, "h2 a span")
            nome = nome_elem.text.strip()
            
            # Preço
            preco = extrair_preco_completo(produto)
            
            # Imagem
            try:
                img_elem = produto.find_element(By.CSS_SELECTOR, "img.s-image")
                imagem = img_elem.get_attribute("src")
            except:
                imagem = ""
            
            # Link
            try:
                link_elem = produto.find_element(By.CSS_SELECTOR, "h2 a")
                link = link_elem.get_attribute("href").split('?')[0]
                link += f"?tag={PARTNER_TAG}"
            except:
                continue
            
            resultados.append((nome, preco, imagem, link))
            print(f"  ✓ {nome[:50]}... - R$ {preco}")
            
        except Exception as e:
            continue
        
        time.sleep(1)
    
    return resultados

# Instalar dependências necessárias:
# pip install selenium webdriver-manager

# Configurar driver
driver = configurar_driver()

todos_produtos = []

try:
    for keyword in KEYWORDS:
        produtos = buscar_produtos(driver, keyword)
        todos_produtos.extend(produtos)
        
        if len(todos_produtos) >= 50:
            break
        
        time.sleep(3)
    
    # Salvar no banco
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        preco TEXT,
        imagem TEXT,
        link TEXT
    )
    """)
    
    cursor.execute("DELETE FROM produtos")
    
    for produto in todos_produtos[:50]:
        cursor.execute("""
        INSERT INTO produtos (nome, preco, imagem, link)
        VALUES (?, ?, ?, ?)
        """, produto)
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ {len(todos_produtos[:50])} produtos salvos!")

finally:
    driver.quit()