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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ===== CONFIGURACOES =====
PARTNER_TAG_AMAZON = "lordumungus-20"
LIMITE_PRODUTOS = 300
KEYWORDS = [
    "fraldas",
    "lenço umedecido",
    "pomada assadura",
    "mamadeira",
    "chupeta",
    "berço",
    "colchão berço",
    "bebê conforto",
    "carrinho de bebe",
    "bolsa maternidade",
    "trocador",
    "banheira bebe",
    "toalha com capuz bebe",
    "body bebe",
    "mijão bebe",
    "macacão bebe",
    "kit higiene bebe",
    "termometro digital bebe",
    "paninho de boca"
]
# =========================

DB_PATH = 'produtos.db'
MAX_POR_BUSCA = 15
PAGINAS_POR_KEYWORD = 3

print("=" * 60)
print(f"🚀 CRAWLER AMAZON - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 60)
print(f"🎯 Limite: {LIMITE_PRODUTOS} produtos")
print(f"🔑 Palavras-chave: {len(KEYWORDS)}")
print(f"📄 Páginas por busca: {PAGINAS_POR_KEYWORD}")
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
    """Extrai preco do produto na Amazon"""
    # Tenta preco inteiro + centavos
    try:
        preco_inteiro = produto.find_element(By.CSS_SELECTOR, ".a-price-whole").text
        preco_centavos = produto.find_element(By.CSS_SELECTOR, ".a-price-fraction").text
        inteiro = re.sub(r'[^\d]', '', preco_inteiro)
        centavos = re.sub(r'[^\d]', '', preco_centavos)
        if inteiro and centavos:
            return f"{inteiro},{centavos}"
    except:
        pass
    
    # Tenta preco completo
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
    
    return "Preco indisponivel"

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
    """Busca produtos na Amazon para uma palavra-chave (MULTIPAGINAS)"""
    print(f"\n🟡 AMAZON - Buscando: {keyword}")
    
    resultados = []
    
    # Loop por multiplas paginas
    for pagina in range(1, PAGINAS_POR_KEYWORD + 1):
        # Verifica se ja atingiu o limite global
        if produtos_coletados + len(resultados) >= LIMITE_PRODUTOS:
            restantes = LIMITE_PRODUTOS - (produtos_coletados + len(resultados))
            if restantes <= 0:
                break
            print(f"  ⚠️ Ultima pagina: so precisamos de mais {restantes}")
        
        print(f"  📄 Pagina {pagina}/{PAGINAS_POR_KEYWORD}")
        
        time.sleep(random.uniform(3, 5))
        
        # Monta URL com paginacao
        if pagina == 1:
            url = f"https://www.amazon.com.br/s?k={keyword}"
        else:
            url = f"https://www.amazon.com.br/s?k={keyword}&page={pagina}"
        
        driver.get(url)
        
        # Aguarda carregar
        time.sleep(4)
        
        # Rola a pagina para carregar tudo
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Encontra produtos
        produtos = driver.find_elements(By.CSS_SELECTOR, "[data-component-type='s-search-result']")
        if not produtos:
            produtos = driver.find_elements(By.CSS_SELECTOR, ".s-result-item")
        
        print(f"  📦 Encontrados {len(produtos)} produtos nesta pagina")
        
        # Calcula quantos pegar nesta pagina
        restantes_global = LIMITE_PRODUTOS - (produtos_coletados + len(resultados))
        max_nesta_pagina = min(MAX_POR_BUSCA, restantes_global, len(produtos))
        
        contador_pagina = 0
        for produto in produtos[:max_nesta_pagina]:
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
                contador_pagina += 1
                print(f"    ✓ {contador_pagina:2d}: {nome[:40]}... - R$ {preco}")
                
            except Exception as e:
                continue
        
        # Se nao encontrou produtos nesta pagina, para
        if contador_pagina == 0:
            print("  ⚠️ Sem produtos nesta pagina, encerrando busca")
            break
        
        # Pequena pausa entre paginas
        if pagina < PAGINAS_POR_KEYWORD:
            time.sleep(random.uniform(2, 4))
    
    print(f"  ✅ Total para '{keyword}': {len(resultados)} produtos")
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
        if i % 50 == 0:
            print(f"  💾 Salvando... {i}/{len(resultados)} produtos")
    
    conn.commit()
    conn.close()
    return True

def mostrar_estatisticas():
    """Mostra estatisticas do banco"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM produtos")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM produtos WHERE preco != 'Preco indisponivel'")
    com_preco = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n📊 ESTATISTICAS FINAIS")
    print(f"  Total produtos: {total}")
    if total > 0:
        print(f"  Com preco: {com_preco} ({com_preco/total*100:.1f}%)")
        print(f"  Sem preco: {total - com_preco}")

def main():
    inicio = time.time()
    
    # Cria a tabela se nao existir
    criar_tabela()
    
    # Mostra quantos produtos existem antes
    antes = contar_produtos()
    print(f"📊 Produtos no banco antes: {antes}")
    
    # Apaga registros anteriores
    if antes > 0:
        print("🗑️ Apagando registros anteriores...")
        limpar_banco()
    
    driver = configurar_driver()
    todos_produtos = []
    
    try:
        for i, keyword in enumerate(KEYWORDS, 1):
            # Verifica se ja atingiu o limite
            if len(todos_produtos) >= LIMITE_PRODUTOS:
                print(f"\n🛑 Limite de {LIMITE_PRODUTOS} produtos atingido!")
                break
            
            print(f"\n{'='*60}")
            print(f"🔎 PALAVRA-CHAVE {i}/{len(KEYWORDS)}: {keyword.upper()}")
            print(f"{'='*60}")
            
            # Busca produtos
            produtos = buscar_amazon(driver, keyword, len(todos_produtos))
            todos_produtos.extend(produtos)
            
            print(f"\n📊 Parcial: {len(todos_produtos)}/{LIMITE_PRODUTOS} produtos")
            
            # Pausa entre buscas
            if len(todos_produtos) < LIMITE_PRODUTOS and i < len(KEYWORDS):
                pausa = random.uniform(5, 8)
                print(f"⏸️  Pausa de {pausa:.1f} segundos antes da proxima busca...")
                time.sleep(pausa)
        
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
            
            # Estatisticas
            mostrar_estatisticas()
        
        tempo_total = time.time() - inicio
        print(f"\n⏱️ Tempo total: {tempo_total:.2f} segundos")
        if len(todos_produtos) > 0:
            print(f"⏱️ Media: {tempo_total/len(todos_produtos):.2f} segundos/produto")
        
    except Exception as e:
        print(f"\n❌ Erro durante execucao: {e}")
    finally:
        driver.quit()
        print("\n👋 Crawler encerrado")

if __name__ == "__main__":
    main()