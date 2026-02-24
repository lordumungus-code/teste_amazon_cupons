import schedule
import time
import subprocess
import logging
import os
import sys
from datetime import datetime

# Configuração de logging
LOG_FILE = 'crawler_agendado.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def executar_comando(comando, descricao, timeout=300):
    """Executa um comando e retorna o resultado"""
    logging.info(f"📌 {descricao}")
    
    try:
        resultado = subprocess.run(
            comando,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if resultado.returncode == 0:
            logging.info(f"✅ {descricao} concluído com sucesso")
            if resultado.stdout:
                # Mostra apenas as últimas linhas
                linhas = resultado.stdout.strip().split('\n')
                for linha in linhas[-5:]:  # Mostra últimas 5 linhas
                    if linha.strip():
                        logging.info(f"   {linha}")
            return True
        else:
            logging.error(f"❌ {descricao} falhou!")
            logging.error(f"Erro: {resultado.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logging.error(f"❌ {descricao} excedeu tempo limite de {timeout}s")
        return False
    except Exception as e:
        logging.error(f"❌ Erro inesperado: {e}")
        return False

def verificar_ambiente():
    """Verifica se tudo está configurado"""
    logging.info("🔍 Verificando ambiente...")
    
    # Verifica se Python está instalado
    python_version = sys.version.split()[0]
    logging.info(f"🐍 Python: {python_version}")
    
    # Railway CLI é opcional
    try:
        subprocess.run(['railway', '--version'], capture_output=True, check=True)
        logging.info("✅ Railway CLI encontrado")
        return True
    except:
        logging.warning("⚠️ Railway CLI não encontrado. Deploy automático desabilitado.")
        return True  # Continua mesmo sem Railway

def executar_ciclo_completo():
    """Executa crawler e depois faz deploy"""
    inicio = time.time()
    logging.info("=" * 60)
    logging.info(f"🚀 INICIANDO CICLO COMPLETO - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    logging.info("=" * 60)
    
    # 1. Verifica ambiente (opcional)
    verificar_ambiente()
    
    # 2. Executa o crawler
    if not executar_comando("python crawler.py", "Executando crawler", timeout=600):
        logging.error("❌ Crawler falhou, abortando ciclo")
        return
    
    # 3. Verifica se o banco foi criado/atualizado
    if os.path.exists("produtos.db"):
        tamanho = os.path.getsize("produtos.db")
        data_mod = datetime.fromtimestamp(os.path.getmtime("produtos.db"))
        logging.info(f"📦 Banco de dados: {tamanho/1024:.2f} KB")
        logging.info(f"🕐 Última modificação: {data_mod.strftime('%d/%m/%Y %H:%M:%S')}")
    else:
        logging.error("❌ Banco de dados não encontrado!")
        return
    
    # 4. Deploy no Railway (opcional - só se tiver CLI)
    try:
        subprocess.run(['railway', '--version'], capture_output=True, check=True)
        executar_comando("railway up --detach", "Fazendo deploy no Railway", timeout=300)
    except:
        logging.info("⏭️ Deploy automático pulado (Railway CLI não disponível)")
    
    tempo_total = time.time() - inicio
    logging.info("=" * 60)
    logging.info(f"✨ CICLO CONCLUÍDO! - {tempo_total:.2f} segundos")
    logging.info("=" * 60)

def status_atual():
    """Mostra o status atual do sistema"""
    logging.info("\n" + "=" * 60)
    logging.info("📊 STATUS DO SISTEMA")
    logging.info("=" * 60)
    
    # Verifica banco
    if os.path.exists("produtos.db"):
        tamanho = os.path.getsize("produtos.db")
        data_mod = datetime.fromtimestamp(os.path.getmtime("produtos.db"))
        
        # Conta produtos
        try:
            import sqlite3
            conn = sqlite3.connect("produtos.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM produtos")
            total = cursor.fetchone()[0]
            conn.close()
            logging.info(f"📦 Banco: {total} produtos | {tamanho/1024:.2f} KB")
        except:
            logging.info(f"📦 Banco: {tamanho/1024:.2f} KB")
        
        logging.info(f"🕐 Última atualização: {data_mod.strftime('%d/%m/%Y %H:%M:%S')}")
    else:
        logging.info("❌ Banco de dados não encontrado")
    
    # Verifica logs
    if os.path.exists(LOG_FILE):
        tamanho_log = os.path.getsize(LOG_FILE)
        data_log = datetime.fromtimestamp(os.path.getmtime(LOG_FILE))
        logging.info(f"📋 Log: {tamanho_log/1024:.2f} KB | {data_log.strftime('%d/%m/%Y %H:%M:%S')}")
    
    logging.info("=" * 60)

def main():
    logging.info("🕐 AGENDADOR INICIADO - Executando a cada 30 minutos")
    logging.info("=" * 60)
    
    # Mostra status inicial
    status_atual()
    
    # Executa imediatamente na primeira vez
    logging.info("\n🚀 Executando primeira coleta...")
    executar_ciclo_completo()
    
    # Agenda para executar a cada 30 minutos
    schedule.every(30).minutes.do(executar_ciclo_completo)
    
    # Agenda para mostrar status a cada hora
    schedule.every().hour.do(status_atual)
    
    logging.info("\n⏰ Agendador configurado - Próxima execução em 30 minutos")
    logging.info("=" * 60)
    
    # Loop principal
    try:
        while True:
            schedule.run_pending()
            time.sleep(10)  # Verifica a cada 10 segundos
    except KeyboardInterrupt:
        logging.info("\n👋 Agendador encerrado pelo usuário")
    except Exception as e:
        logging.error(f"❌ Erro no loop principal: {e}")

if __name__ == "__main__":
    main()