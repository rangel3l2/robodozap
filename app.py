import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar
import pandas as pd
import threading
import time
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import requests
import serial
import uuid
import json
import os
import google.generativeai as genai
import psutil
import atexit
import signal
from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxDriver
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver
from selenium.webdriver.edge.webdriver import WebDriver as EdgeDriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import winreg
import browser_cookie3
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
import random
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# Variáveis globais
driver = None
selenium_thread = None
serial_port = None
CONFIG_FILE = "config.json"
CONFIG_TEMPLATE_FILE = "config.template.json"
current_message = None
cleanup_done = False

# Configuração global (será inicializada mais tarde)
GEMINI_API_KEY = None
WHATSAPP_NUMBER = None
MENU_LINK = None
DELAY_BETWEEN_MESSAGES = (8, 15)  # Range em segundos
MAX_MESSAGES_PER_HOUR = 45
TYPING_SPEED_RANGE = (2, 5)  # Caracteres por segundo
BATCH_SIZE = 30  # Mensagens por lote
REST_BETWEEN_BATCHES = (300, 600)  # 5-10 minutos em segundos

def load_config():
    """Carrega ou cria arquivo de configuração"""
    try:
        if not os.path.exists(CONFIG_FILE):
            if os.path.exists(CONFIG_TEMPLATE_FILE):
                with open(CONFIG_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Solicita dados sensíveis na primeira execução
                config["api_key"] = input("Digite sua Gemini API key: ")
                config["whatsapp"] = {
                    "number": input("Digite seu número WhatsApp: "),
                    "menu_link": input("Digite o link do cardápio: ")
                }
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4)
                return config
            else:
                raise FileNotFoundError("Arquivo config.template.json não encontrado!")
        
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao carregar configuração: {e}")
        return {
            "api_key": "",
            "whatsapp": {
                "number": "",
                "menu_link": ""
            }
        }

def initialize_config():
    """Inicializa as configurações globais"""
    global GEMINI_API_KEY, WHATSAPP_NUMBER, MENU_LINK
    try:
        config = load_config()
        GEMINI_API_KEY = config.get("api_key", "")
        WHATSAPP_NUMBER = config.get("whatsapp", {}).get("number", "")
        MENU_LINK = config.get("whatsapp", {}).get("menu_link", "")
        
        if not all([GEMINI_API_KEY, WHATSAPP_NUMBER, MENU_LINK]):
            raise ValueError("Configuração incompleta")
            
    except Exception as e:
        messagebox.showerror("Erro de Configuração", 
            "Erro ao carregar configurações. Por favor, verifique o arquivo config.json")
        print(f"Erro de inicialização: {e}")
        sys.exit(1)

def get_serial_number():
    # Obtém o endereço MAC e concatena com 211292
    mac = uuid.getnode()
    return f"{mac}211292"

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

class ConfigDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Configurações")
        self.geometry("400x200")
        
        # Carrega configuração existente
        self.config = load_config()
        
        # Serial Number
        serial_frame = tk.Frame(self)
        serial_frame.pack(pady=20)
        
        serial_number = self.config.get('serial_number', get_serial_number())
        
        tk.Label(serial_frame, text="Número Serial:").pack(side=tk.LEFT, padx=5)
        self.serial_entry = tk.Entry(serial_frame, width=30)
        self.serial_entry.insert(0, serial_number)
        self.serial_entry.config(state='readonly')
        self.serial_entry.pack(side=tk.LEFT, padx=5)
        
        # Botões
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="OK", command=self.save_settings).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancelar", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def save_settings(self):
        serial_number = self.serial_entry.get()
        self.config['serial_number'] = serial_number
        save_config(self.config)
        self.destroy()

class SerialValidationDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Validação de Serial")
        self.geometry("400x200")
        self.resizable(False, False)
        
        # Tornar janela modal
        self.transient(parent)
        self.grab_set()
        
        # Centralizar na tela
        self.geometry("+%d+%d" % (
            parent.winfo_rootx() + parent.winfo_width()/2 - 200,
            parent.winfo_rooty() + parent.winfo_height()/2 - 100))

        # Impedir fechamento da janela
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Layout
        tk.Label(self, text="Bem-vindo ao Sistema!", font=('Helvetica', 14, 'bold')).pack(pady=10)
        tk.Label(self, text="Por favor, insira o número serial para continuar:").pack(pady=5)
        
        self.serial_entry = tk.Entry(self, width=40)
        self.serial_entry.pack(pady=10)
        
        self.message_label = tk.Label(self, text="", fg="red")
        self.message_label.pack(pady=5)
        
        tk.Button(self, text="Validar Serial", command=self.validate_serial).pack(pady=10)
        
        # Gerar serial esperado
        self.expected_serial = get_serial_number()

    def validate_serial(self):
        entered_serial = self.serial_entry.get().strip()
        if entered_serial == self.expected_serial:
            config = load_config()
            config['serial_number'] = entered_serial
            save_config(config)
            self.grab_release()
            self.destroy()
            self.parent.deiconify()  # Mostra a janela principal
        else:
            self.message_label.config(
                text="Serial inválido! Por favor, insira o serial correto.",
                fg="red"
            )

def get_default_browser():
    """Detecta o navegador padrão do Windows"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
            r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice") as key:
            browser = winreg.QueryValueEx(key, "ProgId")[0]
            
        browsers = {
            "ChromeHTML": "chrome",
            "FirefoxURL": "firefox",
            "MSEdgeHTM": "edge"
        }
        return browsers.get(browser, "chrome")  # Chrome como fallback
    except:
        return "chrome"  # Fallback seguro

def inicializar_driver(headless=False):
    """Inicializa o driver do navegador padrão com persistência de sessão"""
    browser_type = get_default_browser()
    user_data_dir = os.path.join(os.path.expanduser("~"), "whatsapp_selenium_data")
    os.makedirs(user_data_dir, exist_ok=True)
    
    try:
        if browser_type == "firefox":
            from selenium.webdriver.firefox.options import Options
            options = Options()
            if headless:
                options.add_argument("--headless")
            options.add_argument(f"--profile {user_data_dir}")
            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
            
        elif browser_type == "edge":
            from selenium.webdriver.edge.options import Options
            options = Options()
            if headless:
                options.add_argument("--headless")
            options.add_argument(f"user-data-dir={user_data_dir}")
            service = EdgeService(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=service, options=options)
            
        else:  # chrome como padrão
            from selenium.webdriver.chrome.options import Options
            options = Options()
            if headless:
                options.add_argument("--headless")
            options.add_argument(f"user-data-dir={user_data_dir}")
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        
        return driver
    except Exception as e:
        print(f"Erro ao inicializar driver: {e}")
        return None

# Função para configurar a conexão Serial
def configurar_serial(porta, baudrate=9600):
    try:
        global serial_port
        serial_port = serial.Serial(porta, baudrate, timeout=1)
        messagebox.showinfo("Serial", f"Conexão Serial estabelecida na porta {porta}")
    except Exception as e:
        messagebox.showerror("Erro Serial", f"Erro ao conectar na porta {porta}: {e}")

# Função para gerar mensagem com Gemini API
def gerar_mensagem_pizza_mania(nome):
    try:
        url = "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }
        
        dia_semana = datetime.now().strftime('%A')
        dias_pt = {
            'Monday': 'Segunda-feira',
            'Tuesday': 'Terça-feira',
            'Wednesday': 'Quarta-feira',
            'Thursday': 'Quinta-feira',
            'Friday': 'Sexta-feira',
            'Saturday': 'Sábado',
            'Sunday': 'Domingo'
        }
        dia_pt = dias_pt.get(dia_semana, dia_semana)
        
        prompt = (
            f"Crie uma mensagem divertida sobre {dia_pt} para a Pizzaria Pizza Mania seguindo estas regras:\n"
            "1. Use emojis relevantes e divertidos\n"
            "2. Faça referência ao clima ou situação do dia\n"
            "3. Use negrito com asteriscos (*texto*) para palavras-chave\n"
            "4. Use itálico com underlines (_texto_) para ênfase\n"
            "5. Use o nome *Pizza Mania* pelo menos uma vez na mensagem\n"
            "6. Quebre as linhas de forma adequada para WhatsApp\n"
            "7. Mensagem deve ser curta e envolvente\n"
            "8. Não mencione promoções\n"
            "9. Foque em pizza e diversão\n"
            "10. Use no máximo 3 linhas\n"
            "11. Inclua algo sobre ser a melhor pizzaria"
        )
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 100
            }
        }

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        parte2 = result['candidates'][0]['content']['parts'][0]['text'].strip()
        
        if not parte2:
            raise ValueError("Resposta vazia do Gemini")
            
    except Exception as e:
        print(f"Erro ao gerar mensagem: {e}")
        parte2 = "🌟 Venha para a *Pizza Mania*! _A melhor pizzaria da cidade_ 🍕✨"
    
    # Montagem da mensagem completa com estilo WhatsApp
    mensagem = (
        f"*Boa noite %name%!* 👋\n\n"  # Parte 1 estilizada
        f"{parte2}\n\n"  # Parte 2 gerada pelo Gemini com estilos
        f"📱 _Peça agora_ na *Pizza Mania*: *{WHATSAPP_NUMBER}*\n"  # Parte 3 estilizada
        f"🔍 _Veja nosso cardápio:_ {MENU_LINK}"  # Parte 4 estilizada
    )
    
    return mensagem

def testar_mensagem():
    # Renomear função mas manter nome interno para compatibilidade
    mostrar_preview_mensagem()

def mostrar_preview_mensagem():
    mensagem = gerar_mensagem_pizza_mania("Cliente Teste")
    preview = tk.Toplevel(root)
    preview.title("Preview da Mensagem")
    preview.geometry("600x400")  # Aumentado largura
    
    # Configurar grid weights
    preview.grid_rowconfigure(0, weight=1)
    preview.grid_columnconfigure(0, weight=1)
    
    # Frame para o texto
    text_frame = tk.Frame(preview)
    text_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
    text_frame.grid_columnconfigure(0, weight=1)
    text_frame.grid_rowconfigure(0, weight=1)
    
    text_widget = tk.Text(text_frame, wrap=tk.WORD)
    text_widget.grid(row=0, column=0, sticky='nsew')
    text_widget.insert("1.0", mensagem)
    
    # Scrollbar para o texto
    scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
    scrollbar.grid(row=0, column=1, sticky='ns')
    text_widget.configure(yscrollcommand=scrollbar.set)
    
    # Frame para os botões
    button_frame = tk.Frame(preview)
    button_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 10))
    
    def gerar_nova_mensagem():
        nova_mensagem = gerar_mensagem_pizza_mania("Cliente Teste")
        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", nova_mensagem)
    
    def inserir_no_prompt():
        global current_message
        current_message = text_widget.get("1.0", tk.END).strip()
        # Atualizar área de mensagem principal
        message_display.delete("1.0", tk.END)
        message_display.insert("1.0", current_message)
        start_button.config(state=tk.NORMAL)  # Habilitar botão de envio
        preview.destroy()
    
    # Criar botões com tamanho fixo e padding
    btn_gerar = tk.Button(button_frame, text="Gerar Outra Mensagem", 
                         command=gerar_nova_mensagem, width=25)
    btn_gerar.pack(side=tk.LEFT, padx=5)
    
    btn_inserir = tk.Button(button_frame, text="Inserir Mensagem no Prompt", 
                           command=inserir_no_prompt, width=25)
    btn_inserir.pack(side=tk.LEFT, padx=5)
    
    btn_fechar = tk.Button(button_frame, text="Fechar", 
                          command=preview.destroy, width=15)
    btn_fechar.pack(side=tk.RIGHT, padx=5)

# Função para iniciar o processo de envio em uma thread separada
def start_process_threaded():
    global selenium_thread
    selenium_thread = threading.Thread(target=start_process, daemon=True)
    selenium_thread.start()

class StatusFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        # Barra de progresso
        self.progress_bar = Progressbar(self, orient="horizontal", 
                                      mode="determinate", length=400)
        self.progress_bar.pack(pady=10)
        
        # Status text
        self.status_text = tk.Text(self, height=10, wrap=tk.WORD)
        self.status_text.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

def human_typing(element, text):
    """Simula digitação humana com velocidade variável"""
    for char in text:
        element.send_keys(char)
        delay = random.uniform(0.1, 0.3)
        time.sleep(delay)
        if random.random() < 0.02:  # 2% chance de erro de digitação
            element.send_keys(Keys.BACKSPACE)
            time.sleep(random.uniform(0.1, 0.3))
            element.send_keys(char)

def add_human_behavior(driver):
    """Adiciona comportamentos humanos aleatórios"""
    actions = ActionChains(driver)
    # Movimento aleatório do mouse
    for _ in range(random.randint(1, 3)):
        x = random.randint(100, 700)
        y = random.randint(100, 500)
        actions.move_by_offset(x, y)
    actions.perform()
    
    # Scroll aleatório
    if random.random() < 0.3:  # 30% chance
        driver.execute_script(f"window.scrollBy(0, {random.randint(-100, 100)})")

def modify_start_process():
    """Modificação da função start_process para comportamento mais humano"""
    global driver, current_message
    status_frame = None
    mensagens_enviadas = 0
    hora_inicio = time.time()
    
    try:
        if not csv_file_path.get():
            messagebox.showerror("Erro", "Nenhum arquivo CSV selecionado!")
            return
        
        if not current_message:
            messagebox.showerror("Erro", "Nenhuma mensagem gerada!")
            return

        # Criar e mostrar frame de status
        status_frame = StatusFrame(root)
        status_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        try:
            contatos = pd.read_csv(csv_file_path.get())
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar o arquivo CSV: {e}")
            status_frame.destroy()
            return

        driver = inicializar_driver(headless=False)
        if not driver:
            messagebox.showerror("Erro", "Não foi possível inicializar o navegador!")
            return
            
        driver.get("https://web.whatsapp.com")

        try:
            WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "side")))
            print("WhatsApp Web conectado.")
        except TimeoutException:
            if not driver.window_handles:  # Verifica se o navegador foi fechado
                messagebox.showerror("Erro", 
                    "Alerta de erro, o navegador não pode ser fechado abruptamente, "
                    "então todos os processos abertos deve ser encerrado e o usuario "
                    "deve clicar iniciar envio para enviar novamente e todo o "
                    "processo recomeçara.")
                cleanup_processes()
                return
            else:
                print("Aguardando scan do QR Code...")
                # Aguarda mais tempo para scan manual
                try:
                    WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.ID, "side")))
                except TimeoutException:
                    messagebox.showerror("Erro", "Tempo limite excedido para scan do QR Code")
                    cleanup_processes()
                    return

        total_contatos = len(contatos)
        status_frame.progress_bar["maximum"] = total_contatos
        status_frame.progress_bar["value"] = 0

        for index, row in enumerate(contatos.iterrows()):
            # Verificar limite por hora
            if mensagens_enviadas >= MAX_MESSAGES_PER_HOUR:
                tempo_espera = 3600 - (time.time() - hora_inicio)
                if tempo_espera > 0:
                    status_frame.status_text.insert(tk.END, 
                        f"Aguardando {tempo_espera/60:.0f} minutos para continuar...\n")
                    time.sleep(tempo_espera)
                mensagens_enviadas = 0
                hora_inicio = time.time()

            # Pausa entre lotes
            if index > 0 and index % BATCH_SIZE == 0:
                pausa = random.randint(REST_BETWEEN_BATCHES[0], REST_BETWEEN_BATCHES[1])
                status_frame.status_text.insert(tk.END, 
                    f"Pausa de segurança: {pausa/60:.0f} minutos...\n")
                time.sleep(pausa)

            name = row[1]["name"]
            phone = row[1]["phone"]
            
            # Adicionar comportamentos humanos
            add_human_behavior(driver)
            
            # Abrir chat com delay variável
            driver.get(f"https://web.whatsapp.com/send?phone={phone}")
            time.sleep(random.uniform(3, 5))
            
            try:
                # Aguardar campo de mensagem e simular digitação
                message_box = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
                )
                
                mensagem = current_message.replace("%name%", name)
                human_typing(message_box, mensagem)
                
                # Pequena pausa antes de enviar
                time.sleep(random.uniform(0.5, 1.5))
                
                enviar_btn = WebDriverWait(driver, 30).until(
                    EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]'))
                )
                enviar_btn.click()
                
                mensagens_enviadas += 1
                status_frame.status_text.insert(tk.END, 
                    f"Mensagem enviada para: {name} ({phone})\n")
                
            except Exception as e:
                status_frame.status_text.insert(tk.END, 
                    f"Erro ao enviar para: {name} ({phone}): {e}\n")
                
            # Delay variável entre mensagens
            time.sleep(random.uniform(DELAY_BETWEEN_MESSAGES[0], DELAY_BETWEEN_MESSAGES[1]))
            
            status_frame.progress_bar["value"] = index + 1
            root.update_idletasks()

        if driver:
            driver.quit()
        driver = None
        
        status_frame.status_text.insert(tk.END, "Envio concluído.\n")
        status_frame.status_text.see(tk.END)
    except Exception as e:
        messagebox.showerror("Erro", f"Erro durante o processo: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
            driver = None
        if status_frame and status_frame.winfo_exists():
            status_frame.destroy()
        cleanup_processes()

# Substituir a função start_process original pela nova versão
start_process = modify_start_process

# Fechar o driver do Selenium e Serial ao sair
def cleanup_processes():
    """Limpa todos os processos do Chrome e Selenium"""
    global driver, cleanup_done
    if cleanup_done:
        return
        
    try:
        # Fecha o driver do Selenium adequadamente
        if driver:
            driver.quit()
            driver = None
            
        # Procura e fecha processos do Chrome
        current_pid = os.getpid()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Fecha processos do Chrome relacionados ao selenium
                if proc.info['pid'] != current_pid:
                    if any(name in str(proc.info['name']).lower() 
                          for name in ['chrome', 'chromedriver']):
                        if proc.info['cmdline'] and '--test-type' in ' '.join(proc.info['cmdline']):
                            proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        # Fecha a porta serial se estiver aberta
        if serial_port and serial_port.is_open:
            serial_port.close()
            
    except Exception as e:
        print(f"Erro durante limpeza: {e}")
    finally:
        cleanup_done = True

def on_closing():
    """Função melhorada para fechamento da aplicação"""
    cleanup_processes()
    root.quit()
    root.destroy()

def handle_signals(signum, frame):
    """Manipulador de sinais para capturar interrupções"""
    cleanup_processes()
    sys.exit(0)

def create_menu():
    menubar = tk.Menu(root)
    root.config(menu=menubar)
    
    config_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Configurações", menu=config_menu)
    config_menu.add_command(label="Configurar Serial", command=lambda: ConfigDialog(root))

def initialize_gui():
    # Frame superior
    frame_superior = tk.Frame(root)
    frame_superior.pack(pady=10, fill=tk.X)

    global csv_file_path, message_display, start_button
    csv_file_path = tk.StringVar()

    # Botão para selecionar o arquivo CSV
    csv_label = tk.Label(frame_superior, text="Arquivo CSV:")
    csv_label.grid(row=0, column=0, padx=5, pady=5)
    csv_entry = tk.Entry(frame_superior, textvariable=csv_file_path, width=50)
    csv_entry.grid(row=0, column=1, padx=5, pady=5)
    csv_button = tk.Button(frame_superior, text="Selecionar", 
                          command=lambda: csv_file_path.set(filedialog.askopenfilename()))
    csv_button.grid(row=0, column=2, padx=5, pady=5)

    # Área de exibição da mensagem
    message_frame = tk.Frame(root)
    message_frame.pack(pady=10, fill=tk.BOTH, expand=True)
    
    message_label = tk.Label(message_frame, text="Mensagem atual:")
    message_label.pack(anchor='w', padx=10)
    
    message_display = tk.Text(message_frame, height=6, wrap=tk.WORD)
    message_display.pack(fill=tk.BOTH, expand=True, padx=10)

    # Botão gerar mensagem
    generate_button = tk.Button(root, text="Gerar Mensagem", 
                              command=mostrar_preview_mensagem)
    generate_button.pack(pady=5)

    # Botão para iniciar o envio (inicialmente desabilitado)
    start_button = tk.Button(root, text="Iniciar Envio", 
                            command=start_process_threaded, 
                            state=tk.DISABLED)
    start_button.pack(pady=5)

    # Fechamento seguro da aplicação
    root.protocol("WM_DELETE_WINDOW", on_closing)

def main():
    global root
    
    try:
        # Inicializar configurações primeiro
        initialize_config()
        
        # Registrar handlers de limpeza
        atexit.register(cleanup_processes)
        signal.signal(signal.SIGINT, handle_signals)
        signal.signal(signal.SIGTERM, handle_signals)
        
        root = tk.Tk()
        root.withdraw()  # Esconde a janela principal inicialmente
        
        config = load_config()
        if not config.get('serial_number'):
            SerialValidationDialog(root)
        else:
            if config['serial_number'] == get_serial_number():
                root.deiconify()  # Mostra a janela principal
            else:
                SerialValidationDialog(root)
        
        root.title("Envio de Mensagens - Pizza Mania")
        root.geometry("800x600")  # Increased window size
        
        create_menu()
        initialize_gui()
        
        try:
            root.mainloop()
        finally:
            cleanup_processes()
            
    except Exception as e:
        messagebox.showerror("Erro Fatal", str(e))
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Erro fatal: {e}")
    finally:
        cleanup_processes()
