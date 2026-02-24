import os
import time
import sqlite3
import re
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# Tag de afiliado Amazon
PARTNER_TAG_AMAZON = "lordumungus-20"

# Palavras-chave para busca (foco em bebês)
KEYWORDS = ["bebe", "bebê", "fraldas", "mamadeira", "carrinho de bebe", "brinquedos bebe"]

# Banco local
DB_PATH = 'produtos.db'
print(f"📁 CRAWLER: Salvando banco em: {DB_PATH}")

def configurar_driver():
    """Configura o Chrome em modo stealth"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# ==================== AMAZON ====================
def extrair_nome_amazon(produto):
    """Extrai nome do produto na Amazon"""
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
    """Extrai preço do produto na Amazon"""
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
            preco_texto = preco_texto.replace('R$', '').replace('.', '').strip()
            match = re.search(r'[\d,]+', preco_texto)
            if match:
                return match.group()
        except:
            continue
    
    return "Preço indisponível"

def extrair_imagem_amazon(produto):
    """Extrai URL da imagem na Amazon"""
    try:
        img = produto.find_element(By.CSS_SELECTOR, "img.s-image")
        src = img.get_attribute("src")
        if src and src.startswith("http"):
            return src
    except:
        pass
    return "https://via.placeholder.com/200x200?text=Amazon"

def extrair_link_amazon(produto):
    """Extrai link do produto na Amazon e adiciona tag de afiliado"""
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
                link = link.split('/ref=')[0].split('?')[0]
                link += f"?tag={PARTNER_TAG_AMAZON}"
                return link
        except:
            continue
    return None

def buscar_amazon(driver, keyword):
    """Busca produtos na Amazon para uma palavra-chave"""
    print(f"\n🟡 AMAZON - Buscando: {keyword}")
    
    time.sleep(random.uniform(2, 4))
    
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
    
    for produto in produtos[:12]:
        try:
            nome = extrair_nome_amazon(produto)
            if not nome:
                continue
            
            preco = extrair_preco_amazon(produto)
            imagem = extrair_imagem_amazon(produto)
            link = extrair_link_amazon(produto)
            
            if not link:
                continue
            
            # SEM a coluna loja - apenas 4 campos
            resultados.append((nome, preco, imagem, link))
            contador += 1
            print(f"  ✓ {contador:2d}: {nome[:40]}... - R$ {preco}")
            
        except Exception as e:
            continue
        
        time.sleep(0.3)
    
    return resultados

def criar_tabela():
    """Cria a tabela SEM a coluna loja"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        preco TEXT,
        imagem TEXT,
        link TEXT,
        data_coleta TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Tabela 'produtos' criada/verificada (sem coluna loja)")

def contar_produtos():
    """Conta quantos produtos existem no banco"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM produtos")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def atualizar_banco(resultados):
    """Salva os resultados no banco de dados"""
    if not resultados:
        print("❌ Nenhum resultado para salvar!")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Conta antes de limpar
    antes = contar_produtos()
    
    # Limpa produtos antigos
    cursor.execute("DELETE FROM produtos")
    
    # Insere os novos produtos (apenas 4 campos)
    for i, produto in enumerate(resultados, 1):
        cursor.execute("""
        INSERT INTO produtos (nome, preco, imagem, link)
        VALUES (?, ?, ?, ?)
        """, produto)
        if i % 10 == 0:
            print(f"  💾 Salvando... {i} produtos")
    
    conn.commit()
    
    # Verifica quantos produtos foram salvos
    depois = contar_produtos()
    conn.close()
    
    print(f"\n✅ {depois} produtos salvos com sucesso!")
    print(f"   (Antes: {antes} produtos)")

# ==================== MAIN ====================
def main():
    print("=" * 60)
    print("🚀 CRAWLER AMAZON - PROMOÇÕES PARA BEBÊS")
    print("=" * 60)
    print(f"🎯 Tag de afiliado: {PARTNER_TAG_AMAZON}")
    print(f"📦 Palavras-chave: {', '.join(KEYWORDS)}")
    print()
    
    # Remove banco antigo se existir (para garantir estrutura correta)
    if os.path.exists(DB_PATH):
        print("🗑️ Removendo banco antigo...")
        os.remove(DB_PATH)
    
    # Cria nova tabela
    criar_tabela()
    
    driver = configurar_driver()
    todos_produtos = []
    
    try:
        for keyword in KEYWORDS:
            print(f"\n{'='*60}")
            print(f"🔎 PALAVRA-CHAVE: {keyword.upper()}")
            print(f"{'='*60}")
            
            produtos_amazon = buscar_amazon(driver, keyword)
            todos_produtos.extend(produtos_amazon)
            
            print(f"\n📊 Parcial: {len(todos_produtos)} produtos")
            
            if len(todos_produtos) >= 48:
                print("\n🛑 Atingido limite de 48 produtos")
                break
            
            time.sleep(random.uniform(3, 5))
        
        print(f"\n{'='*60}")
        print(f"📊 RESUMO FINAL")
        print(f"{'='*60}")
        print(f"Total: {len(todos_produtos)} produtos da Amazon")
        
        if len(todos_produtos) == 0:
            print("\n❌ Nenhum produto encontrado!")
            driver.quit()
            return
        
        atualizar_banco(todos_produtos)
        
    except Exception as e:
        print(f"\n❌ Erro durante execução: {e}")
    finally:
        driver.quit()
        print("\n👋 Crawler encerrado")

if __name__ == "__main__":
    main()