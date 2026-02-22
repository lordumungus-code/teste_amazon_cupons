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
    
    # Descomente para ver o navegador (útil para debug)
    # options.add_argument("--headless=new")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def extrair_nome(produto):
    """Extrai nome do produto - VÁRIAS TENTATIVAS"""
    selectores_nome = [
        "h2 a span",
        "h2",
        ".a-size-base-plus.a-link-normal.a-text-normal",
        ".a-size-medium.a-color-base.a-text-normal",
        "span.a-text-normal"
    ]
    
    for seletor in selectores_nome:
        try:
            elemento = produto.find_element(By.CSS_SELECTOR, seletor)
            nome = elemento.text.strip()
            if nome and len(nome) > 5:  # Nome válido
                return nome
        except:
            continue
    
    return None

def extrair_preco(produto):
    """Extrai preço - VÁRIAS TENTATIVAS"""
    
    # Tenta 1: Preço inteiro + centavos
    try:
        preco_inteiro = produto.find_element(By.CSS_SELECTOR, ".a-price-whole").text
        preco_centavos = produto.find_element(By.CSS_SELECTOR, ".a-price-fraction").text
        inteiro = re.sub(r'[^\d]', '', preco_inteiro)
        centavos = re.sub(r'[^\d]', '', preco_centavos)
        if inteiro and centavos:
            return f"{inteiro},{centavos}"
    except:
        pass
    
    # Tenta 2: Preço completo
    selectores_preco = [
        ".a-price .a-offscreen",
        ".a-price-whole",
        "span.a-price",
        ".a-color-base.a-text-bold"
    ]
    
    for seletor in selectores_preco:
        try:
            elemento = produto.find_element(By.CSS_SELECTOR, seletor)
            preco_texto = elemento.text.strip()
            # Extrai números e vírgula/ponto
            match = re.search(r'[\d.,]+', preco_texto)
            if match:
                return match.group().replace('.', ',')
        except:
            continue
    
    return "Preço indisponível"

def extrair_imagem(produto):
    """Extrai URL da imagem"""
    try:
        # Tenta imagem principal
        img = produto.find_element(By.CSS_SELECTOR, "img.s-image")
        src = img.get_attribute("src")
        if src and src.startswith("http"):
            return src
    except:
        pass
    
    try:
        # Tenta qualquer imagem
        img = produto.find_element(By.CSS_SELECTOR, "img")
        src = img.get_attribute("src")
        if src and src.startswith("http"):
            return src
    except:
        pass
    
    return "https://via.placeholder.com/200x200?text=Sem+Imagem"

def extrair_link(produto):
    """Extrai link do produto"""
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
                # Limpa o link e adiciona a tag de afiliado
                link = link.split('?')[0]
                link += f"?tag={PARTNER_TAG}"
                return link
        except:
            continue
    
    return None

def buscar_produtos(driver, keyword):
    print(f"\n🔍 Buscando produtos para: {keyword}")
    
    url = f"https://www.amazon.com.br/s?k={keyword}"
    driver.get(url)
    
    # Aguarda carregar
    time.sleep(3)
    
    # Rola a página para carregar tudo
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    # Encontra todos os produtos
    produtos = driver.find_elements(By.CSS_SELECTOR, "[data-component-type='s-search-result']")
    
    if not produtos:
        produtos = driver.find_elements(By.CSS_SELECTOR, ".s-result-item")
    
    print(f"  📦 Encontrados {len(produtos)} produtos")
    
    resultados = []
    contador = 0
    erros = 0
    
    for i, produto in enumerate(produtos[:30]):  # Pega até 30 por keyword
        try:
            # Extrai nome (obrigatório)
            nome = extrair_nome(produto)
            if not nome:
                erros += 1
                continue
            
            # Extrai outros campos
            preco = extrair_preco(produto)
            imagem = extrair_imagem(produto)
            link = extrair_link(produto)
            
            if not link:  # Link é obrigatório
                erros += 1
                continue
            
            resultados.append((nome, preco, imagem, link))
            contador += 1
            print(f"  ✓ {contador:2d}. {nome[:50]}... - R$ {preco}")
            
        except Exception as e:
            erros += 1
            continue
        
        time.sleep(0.5)
    
    print(f"  → Para '{keyword}': {contador} produtos extraídos, {erros} ignorados")
    return resultados

def contar_produtos_banco():
    """Conta quantos produtos tem no banco"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM produtos")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

print("🚀 Iniciando crawler com Selenium...")
driver = configurar_driver()
todos_produtos = []
total_geral = 0

try:
    for keyword in KEYWORDS:
        produtos = buscar_produtos(driver, keyword)
        todos_produtos.extend(produtos)
        total_geral += len(produtos)
        print(f"  → Total acumulado: {total_geral} produtos")
        
        if len(todos_produtos) >= 50:
            print("  🛑 Atingido limite de 50 produtos")
            break
        
        time.sleep(3)
    
    print(f"\n📊 TOTAL GERAL: {len(todos_produtos)} produtos encontrados")
    
    if len(todos_produtos) == 0:
        print("❌ Nenhum produto encontrado!")
        print("⚠️ Possíveis causas:")
        print("   - Amazon bloqueou o acesso")
        print("   - Seletores CSS desatualizados")
        print("   - Problema de rede")
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
    count_final = contar_produtos_banco()
    print(f"📊 Verificação final: {count_final} produtos no banco")
    
    # Mostra os primeiros produtos como exemplo
    if count_final > 0:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT nome, preco FROM produtos LIMIT 3")
        print("\n📋 Primeiros produtos salvos:")
        for nome, preco in cursor.fetchall():
            print(f"  • {nome[:60]}... - R$ {preco}")
        conn.close()

finally:
    driver.quit()
    print("👋 Driver encerrado")