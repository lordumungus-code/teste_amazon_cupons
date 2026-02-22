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

# Tags de afiliado
PARTNER_TAG_AMAZON = "lordumungus-20"
PARTNER_TAG_MAGALU = "lordumungus"  # Sua tag do Magalu

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
    
    # Descomente para ver o navegador (útil para debug)
    # options.add_argument("--headless=new")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# ==================== AMAZON ====================
def extrair_nome_amazon(produto):
    selectores = [
        "h2 a span",
        "h2",
        ".a-size-base-plus.a-link-normal.a-text-normal",
        ".a-size-medium.a-color-base.a-text-normal",
        "span.a-text-normal"
    ]
    
    for seletor in selectores:
        try:
            elemento = produto.find_element(By.CSS_SELECTOR, seletor)
            nome = elemento.text.strip()
            if nome and len(nome) > 5:
                return nome
        except:
            continue
    return None

def extrair_preco_amazon(produto):
    # Tenta preço inteiro + centavos
    try:
        preco_inteiro = produto.find_element(By.CSS_SELECTOR, ".a-price-whole").text
        preco_centavos = produto.find_element(By.CSS_SELECTOR, ".a-price-fraction").text
        inteiro = re.sub(r'[^\d]', '', preco_inteiro)
        centavos = re.sub(r'[^\d]', '', preco_centavos)
        if inteiro and centavos:
            return f"{inteiro},{centavos}"
    except:
        pass
    
    # Tenta preço completo
    selectores_preco = [
        ".a-price .a-offscreen",
        ".a-price-whole",
        "span.a-price"
    ]
    
    for seletor in selectores_preco:
        try:
            elemento = produto.find_element(By.CSS_SELECTOR, seletor)
            preco_texto = elemento.text.strip()
            match = re.search(r'[\d.,]+', preco_texto)
            if match:
                return match.group().replace('.', ',')
        except:
            continue
    
    return "Preço indisponível"

def extrair_imagem_amazon(produto):
    try:
        img = produto.find_element(By.CSS_SELECTOR, "img.s-image")
        src = img.get_attribute("src")
        if src and src.startswith("http"):
            return src
    except:
        pass
    return "https://via.placeholder.com/200x200?text=Amazon"

def extrair_link_amazon(produto):
    selectores_link = [
        "h2 a",
        ".a-link-normal.s-no-outline",
        "a.a-link-normal"
    ]
    
    for seletor in selectores_link:
        try:
            link_elem = produto.find_element(By.CSS_SELECTOR, seletor)
            link = link_elem.get_attribute("href")
            if link and "amazon.com.br" in link:
                link = link.split('?')[0]
                link += f"?tag={PARTNER_TAG_AMAZON}"
                return link
        except:
            continue
    return None

# ==================== MAGALU ====================
def extrair_nome_magalu(produto):
    """Extrai nome do produto no Magalu"""
    selectores = [
        "[data-testid='product-title']",
        "h2.sc-eDvSVe",
        ".sc-khIgEk",
        "h2",
        ".product-title",
        "a.sc-dLMFU h2",
        "span.sc-kpDqfm"
    ]
    
    for seletor in selectores:
        try:
            elemento = produto.find_element(By.CSS_SELECTOR, seletor)
            nome = elemento.text.strip()
            if nome and len(nome) > 5:
                return nome
        except:
            continue
    return None

def extrair_preco_magalu(produto):
    """Extrai preço do produto no Magalu"""
    selectores_preco = [
        "[data-testid='price-value']",
        ".sc-bXCLTC",
        ".sc-bwCtUz",
        ".price-tag",
        ".andes-money-amount__fraction",
        "div.sc-fqkvVR",
        "span.sc-iGgWBj"
    ]
    
    for seletor in selectores_preco:
        try:
            elemento = produto.find_element(By.CSS_SELECTOR, seletor)
            preco_texto = elemento.text.strip()
            # Remove R$ e pontos, mantém vírgula
            preco_texto = preco_texto.replace('R$', '').replace('.', '').strip()
            match = re.search(r'[\d,]+', preco_texto)
            if match:
                return match.group()
        except:
            continue
    
    return "Preço indisponível"

def extrair_imagem_magalu(produto):
    """Extrai URL da imagem no Magalu"""
    selectores_img = [
        "img.sc-fqkvVR",
        "img[data-testid='image']",
        "img"
    ]
    
    for seletor in selectores_img:
        try:
            img = produto.find_element(By.CSS_SELECTOR, seletor)
            src = img.get_attribute("src")
            if src and src.startswith("http"):
                # Tenta pegar imagem maior
                src = src.replace("50x50", "200x200").replace("100x100", "200x200")
                return src
        except:
            continue
    
    return "https://via.placeholder.com/200x200?text=Magalu"

def extrair_link_magalu(produto):
    """Extrai link do produto no Magalu e adiciona tag de afiliado"""
    selectores_link = [
        "a.sc-dLMFU",
        "a[data-testid='product-card-link']",
        "a"
    ]
    
    for seletor in selectores_link:
        try:
            link_elem = produto.find_element(By.CSS_SELECTOR, seletor)
            link = link_elem.get_attribute("href")
            if link and "magazineluiza.com.br" in link:
                # Limpa o link e adiciona a tag de afiliado
                # Formato correto para afiliado Magalu: ?parceiro=SEU_ID
                if '?' in link:
                    link = link.split('?')[0]
                link += f"?parceiro={PARTNER_TAG_MAGALU}"
                return link
        except:
            continue
    return None

# ==================== BUSCA AMAZON ====================
def buscar_amazon(driver, keyword):
    print(f"\n🟡 AMAZON - Buscando: {keyword}")
    url = f"https://www.amazon.com.br/s?k={keyword}"
    driver.get(url)
    time.sleep(3)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    produtos = driver.find_elements(By.CSS_SELECTOR, "[data-component-type='s-search-result']")
    if not produtos:
        produtos = driver.find_elements(By.CSS_SELECTOR, ".s-result-item")
    
    print(f"  📦 Encontrados {len(produtos)} produtos na Amazon")
    
    resultados = []
    contador = 0
    
    for produto in produtos[:12]:  # Limite de 12 por loja
        try:
            nome = extrair_nome_amazon(produto)
            if not nome:
                continue
            
            preco = extrair_preco_amazon(produto)
            imagem = extrair_imagem_amazon(produto)
            link = extrair_link_amazon(produto)
            
            if not link:
                continue
            
            resultados.append((nome, preco, imagem, link, "Amazon"))
            contador += 1
            print(f"  ✓ Amazon {contador:2d}: {nome[:40]}... - R$ {preco}")
            
        except Exception as e:
            continue
        
        time.sleep(0.5)
    
    return resultados

# ==================== BUSCA MAGALU ====================
def buscar_magalu(driver, keyword):
    print(f"\n🔵 MAGALU - Buscando: {keyword}")
    url = f"https://www.magazineluiza.com.br/busca/{keyword}/"
    driver.get(url)
    time.sleep(4)  # Magalu pode ser mais lento
    
    # Rola a página para carregar mais produtos
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    # Tenta diferentes seletores para produtos do Magalu
    produtos = driver.find_elements(By.CSS_SELECTOR, "[data-testid='product-list'] > div")
    if not produtos:
        produtos = driver.find_elements(By.CSS_SELECTOR, ".sc-eDvSVe")
    if not produtos:
        produtos = driver.find_elements(By.CSS_SELECTOR, ".sc-iapWAC")
    if not produtos:
        produtos = driver.find_elements(By.CSS_SELECTOR, "li[data-testid='product-card']")
    
    print(f"  📦 Encontrados {len(produtos)} produtos no Magalu")
    
    resultados = []
    contador = 0
    
    for produto in produtos[:12]:  # Limite de 12 por loja
        try:
            nome = extrair_nome_magalu(produto)
            if not nome:
                continue
            
            preco = extrair_preco_magalu(produto)
            imagem = extrair_imagem_magalu(produto)
            link = extrair_link_magalu(produto)
            
            if not link:
                continue
            
            resultados.append((nome, preco, imagem, link, "Magalu"))
            contador += 1
            print(f"  ✓ Magalu {contador:2d}: {nome[:40]}... - R$ {preco}")
            
        except Exception as e:
            continue
        
        time.sleep(0.5)
    
    return resultados

# ==================== ATUALIZAR BANCO ====================
def atualizar_banco(resultados):
    """Salva os resultados no banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Cria a tabela se não existir
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        preco TEXT,
        imagem TEXT,
        link TEXT,
        loja TEXT
    )
    """)
    
    # Limpa produtos antigos (opcional - comentar se quiser acumular)
    cursor.execute("DELETE FROM produtos")
    print("🗑️ Banco antigo limpo")
    
    # Insere os novos produtos
    for i, produto in enumerate(resultados[:48], 1):  # Máximo 48 produtos (24 de cada loja)
        cursor.execute("""
        INSERT INTO produtos (nome, preco, imagem, link, loja)
        VALUES (?, ?, ?, ?, ?)
        """, produto)
        if i % 10 == 0:
            print(f"  💾 Salvando... {i} produtos")
    
    conn.commit()
    
    # Verifica quantos produtos foram salvos
    cursor.execute("SELECT COUNT(*) FROM produtos")
    count = cursor.fetchone()[0]
    cursor.execute("SELECT loja, COUNT(*) FROM produtos GROUP BY loja")
    stats = cursor.fetchall()
    conn.close()
    
    print(f"\n✅ {count} produtos salvos com sucesso!")
    for loja, qtd in stats:
        print(f"   • {loja}: {qtd} produtos")

# ==================== MAIN ====================
print("🚀 Iniciando crawler multi-lojas (Amazon + Magalu)")
print(f"🎯 Tags: Amazon={PARTNER_TAG_AMAZON}, Magalu={PARTNER_TAG_MAGALU}")
print("=" * 50)

driver = configurar_driver()
todos_produtos = []
total_amazon = 0
total_magalu = 0

try:
    for keyword in KEYWORDS:
        print(f"\n{'='*50}")
        print(f"🔎 PALAVRA-CHAVE: {keyword.upper()}")
        print(f"{'='*50}")
        
        # Busca na Amazon
        produtos_amazon = buscar_amazon(driver, keyword)
        todos_produtos.extend(produtos_amazon)
        total_amazon += len(produtos_amazon)
        
        # Pequena pausa entre lojas
        time.sleep(2)
        
        # Busca no Magalu
        produtos_magalu = buscar_magalu(driver, keyword)
        todos_produtos.extend(produtos_magalu)
        total_magalu += len(produtos_magalu)
        
        print(f"\n📊 Parcial: Amazon={total_amazon}, Magalu={total_magalu}, Total={len(todos_produtos)}")
        
        if len(todos_produtos) >= 48:
            print("\n🛑 Atingido limite de 48 produtos")
            break
        
        time.sleep(3)
    
    print(f"\n{'='*50}")
    print(f"📊 RESUMO FINAL")
    print(f"{'='*50}")
    print(f"Amazon: {total_amazon} produtos")
    print(f"Magalu: {total_magalu} produtos")
    print(f"Total: {len(todos_produtos)} produtos")
    
    if len(todos_produtos) == 0:
        print("\n❌ Nenhum produto encontrado!")
        print("⚠️ Possíveis causas:")
        print("   - Sites bloquearam o acesso")
        print("   - Seletores CSS desatualizados")
        print("   - Problema de rede")
        driver.quit()
        exit()
    
    # Salva no banco
    atualizar_banco(todos_produtos)

finally:
    driver.quit()
    print("\n👋 Driver encerrado")