import os
import time
import sqlite3
import re
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# Configurações
PARTNER_TAG_AMAZON = "lordumungus-20"
KEYWORDS = ["bebe", "bebê", "fraldas", "mamadeira", "carrinho de bebe", "brinquedos bebe","bebe conforto", "bebê conforto"]
LIMITE_PRODUTOS = 100  # ← ALTERADO PARA 100
DB_PATH = 'produtos.db'

print("=" * 60)
print(f"🚀 CRAWLER AMAZON - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 60)
print(f"🎯 Limite: {LIMITE_PRODUTOS} produtos")
print(f"📦 Banco: {DB_PATH}")
print()

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

def buscar_amazon(driver, keyword, produtos_coletados):
    """Busca produtos na Amazon para uma palavra-chave"""
    print(f"\n🟡 AMAZON - Buscando: {keyword}")
    
    time.sleep(random.uniform(2, 4))
    
    url = f"https://www.amazon.com.br/s?k={keyword}"
    driver.get(url)
    
    time.sleep(3)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    # Encontra produtos
    produtos = driver.find_elements(By.CSS_SELECTOR, "[data-component-type='s-search-result']")
    if not produtos:
        produtos = driver.find_elements(By.CSS_SELECTOR, ".s-result-item")
    
    print(f"  📦 Encontrados {len(produtos)} produtos disponíveis")
    
    resultados = []
    contador = 0
    
    # Calcula quantos ainda podemos pegar
    restantes = LIMITE_PRODUTOS - produtos_coletados
    max_por_busca = min(12, restantes)  # Pega no máximo 12 por busca
    
    print(f"  🎯 Vamos pegar até {max_por_busca} produtos")
    
    for produto in produtos[:max_por_busca]:
        try:
            nome = extrair_nome_amazon(produto)
            if not nome:
                continue
            
            preco = extrair_preco_amazon(produto)
            imagem = extrair_imagem_amazon(produto)
            link = extrair_link_amazon(produto)
            
            if not link:
                continue
            
            resultados.append((nome, preco, imagem, link))
            contador += 1
            print(f"  ✓ {contador:2d}: {nome[:40]}... - R$ {preco}")
            
        except Exception as e:
            continue
        
        time.sleep(0.3)
    
    return resultados

def criar_tabela():
    """Cria a tabela no banco de dados"""
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
    print("✅ Tabela 'produtos' verificada/criada")

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

def limpar_banco():
    """Apaga todos os registros anteriores"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM produtos")
    conn.commit()
    conn.close()
    print("🗑️ Registros anteriores apagados")

def salvar_produtos(resultados):
    """Salva os produtos no banco"""
    if not resultados:
        print("❌ Nenhum resultado para salvar!")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Insere os produtos
    for i, produto in enumerate(resultados, 1):
        cursor.execute("""
        INSERT INTO produtos (nome, preco, imagem, link)
        VALUES (?, ?, ?, ?)
        """, produto)
        if i % 20 == 0:
            print(f"  💾 Salvando... {i} produtos")
    
    conn.commit()
    conn.close()
    return True

def main():
    inicio = time.time()
    
    # Cria a tabela se não existir
    criar_tabela()
    
    # Mostra quantos produtos existem antes
    antes = contar_produtos()
    print(f"📊 Produtos no banco antes: {antes}")
    
    # Pergunta se quer apagar (modo automático sempre apaga)
    if antes > 0:
        print("🗑️ Apagando registros anteriores...")
        limpar_banco()
    
    driver = configurar_driver()
    todos_produtos = []
    
    try:
        for keyword in KEYWORDS:
            # Verifica se já atingiu o limite
            if len(todos_produtos) >= LIMITE_PRODUTOS:
                print(f"\n🛑 Limite de {LIMITE_PRODUTOS} produtos atingido!")
                break
            
            print(f"\n{'='*60}")
            print(f"🔎 PALAVRA-CHAVE: {keyword.upper()}")
            print(f"{'='*60}")
            
            # Busca produtos
            produtos = buscar_amazon(driver, keyword, len(todos_produtos))
            todos_produtos.extend(produtos)
            
            print(f"\n📊 Parcial: {len(todos_produtos)}/{LIMITE_PRODUTOS} produtos")
            
            # Pausa entre buscas
            if len(todos_produtos) < LIMITE_PRODUTOS:
                time.sleep(random.uniform(3, 5))
        
        print(f"\n{'='*60}")
        print(f"📊 RESUMO FINAL")
        print(f"{'='*60}")
        print(f"✅ Total coletado: {len(todos_produtos)} produtos")
        
        if len(todos_produtos) == 0:
            print("\n❌ Nenhum produto encontrado!")
            driver.quit()
            return
        
        # Salva no banco
        if salvar_produtos(todos_produtos):
            depois = contar_produtos()
            print(f"\n✅ {depois} produtos salvos com sucesso!")
            
            # Estatísticas de preço
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM produtos WHERE preço = 'Preço indisponível'")
            sem_preco = cursor.fetchone()[0]
            conn.close()
            
            if sem_preco > 0:
                print(f"⚠️ {sem_preco} produtos sem preço disponível")
        
        tempo_total = time.time() - inicio
        print(f"⏱️ Tempo total: {tempo_total:.2f} segundos")
        
    except Exception as e:
        print(f"\n❌ Erro durante execução: {e}")
    finally:
        driver.quit()
        print("\n👋 Crawler encerrado")

if __name__ == "__main__":
    main()