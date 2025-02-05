import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar
import pandas as pd
import threading
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import requests
import json
import os
import atexit
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from tkhtmlview import HTMLLabel

# Configurações globais
CONFIG_FILE = "config.json"
CONFIG_TEMPLATE_FILE = "config.template.json"
COOKIES_FILE = "whatsapp_cookies.pkl"
USER_DATA_DIR = os.path.join(os.getcwd(), "whatsapp_selenium_data")

# Variáveis globais
driver = None
current_message = None
DELAY_BETWEEN_MESSAGES = 5  # Segundos
MAX_MESSAGES_PER_HOUR = 45
BATCH_SIZE = 30

# Configurações da API
GEMINI_API_KEY = None
WHATSAPP_NUMBER = None
MENU_LINK = None

# Adicionar constantes para WhatsApp
WHATSAPP_QR_SELECTOR = "#app div[data-testid='qrcode']"
WHATSAPP_CHAT_LIST_SELECTOR = "div[data-testid='chat-list']"
WHATSAPP_LOGIN_STATUS_FILE = "whatsapp_login_status.json"

def load_config():
    """Carrega configurações"""
    if not os.path.exists(CONFIG_FILE):
        if not os.path.exists(CONFIG_TEMPLATE_FILE):
            raise FileNotFoundError("Arquivo config.template.json não encontrado!")
            
        with open(CONFIG_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            config["api_key"] = input("Digite sua Gemini API key: ")
            config["whatsapp"] = {
                "number": input("Digite seu número WhatsApp: "),
                "menu_link": input("Digite o link do cardápio: ")
            }
            
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        return config
        
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def initialize_config():
    """Inicializa configurações globais"""
    global GEMINI_API_KEY, WHATSAPP_NUMBER, MENU_LINK
    config = load_config()
    GEMINI_API_KEY = config.get("api_key", "")
    WHATSAPP_NUMBER = config.get("whatsapp", {}).get("number", "")
    MENU_LINK = config.get("whatsapp", {}).get("menu_link", "")

def initialize_driver(headless=True):
    """Inicializa Chrome WebDriver com opção headless"""
    options = Options()
    if headless:
        options.add_argument("--headless=new")  # Novo modo headless do Chrome
        options.add_argument("--window-size=1920,1080")  # Resolução necessária
    options.add_argument(f"user-data-dir={USER_DATA_DIR}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-notifications")
    service = ChromeService(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def get_dia_semana():
    """Retorna o dia da semana atual em português"""
    dias = {
        'Monday': 'Segunda-feira',
        'Tuesday': 'Terça-feira',
        'Wednesday': 'Quarta-feira',
        'Thursday': 'Quinta-feira',
        'Friday': 'Sexta-feira',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo'
    }
    return dias[datetime.now().strftime('%A')]

def gerar_mensagem_pizza_mania(nome):
    """Gera mensagem personalizada via Gemini API"""
    try:
        url = "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }
        
        dia_atual = get_dia_semana()
        
        prompt = {
            "contents": [{
                "role": "user",
                "parts": [{
                    "text": (
                        f"Crie uma mensagem divertida e amigável para uma pizzaria seguindo estas regras:\n"
                        f"1. NÃO inclua saudação inicial ou nome\n"
                        f"2. Use muitos emojis relevantes (pizza, comida, diversão)\n"
                        f"3. Fale sobre como é bom comer pizza hoje\n"
                        f"4. Use o nome *Pizza Mania* mencionando que é a melhor pizzaria\n"
                        f"5. NÃO mencione promoções, descontos ou cupons\n"
                        f"6. Use negrito com *texto* em palavras-chave\n"
                        f"7. Use itálico com _texto_ para ênfase\n"
                        f"8. Mantenha a mensagem curta (máximo 3 linhas)\n"
                        f"9. Seja divertido e acolhedor\n"
                        f"10. Foque em sabor, qualidade e momentos felizes\n"
                        f"11. NÃO inclua valores ou preços\n"
                        f"12. NÃO mencione horários de funcionamento\n"
                        f"13. Apenas crie um texto amigável sobre pizza\n"
                        f"14. Encerre com uma chamada para pedir pizza"
                    )
                }]
            }],
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 100
            }
        }

        response = requests.post(url, json=prompt, headers=headers)
        corpo_mensagem = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            
    except Exception as e:
        print(f"Erro ao gerar mensagem: {e}")
        corpo_mensagem = "🌟 Venha para a *Pizza Mania*! _A melhor pizzaria da cidade_ 🍕✨"
    
    # Formato final da mensagem com ordem específica
    mensagem_completa = (
        f"*Boa noite {nome}!* 👋\n\n"  # Saudação inicial fixa
        f"Hoje é *{dia_atual}*! 📅\n\n"  # Dia da semana
        f"{corpo_mensagem}\n\n"  # Corpo da mensagem gerado pela IA
        f"📱 _Peça agora_ na *Pizza Mania*: *{WHATSAPP_NUMBER}*\n"  # Contato
        f"🔍 _Veja nosso cardápio:_ {MENU_LINK}"  # Link do cardápio
    )
    
    return mensagem_completa

def mostrar_preview_mensagem():
    """Mostra preview da mensagem com botões de ação"""
    mensagem = gerar_mensagem_pizza_mania("Cliente Teste")
    
    # Criar janela de preview
    preview = tk.Toplevel(root)
    preview.title("Preview da Mensagem")
    preview.geometry("600x500")
    preview.resizable(False, False)
    
    # Container principal
    main_container = tk.Frame(preview, padx=20, pady=20)
    main_container.pack(fill=tk.BOTH, expand=True)
    
    # Variável para armazenar a mensagem atual
    current_preview_message = mensagem
    
    # Preview da mensagem
    html_preview = HTMLLabel(
        main_container,
        html=f"<div style='font-family: \"Segoe UI Emoji\", sans-serif; font-size: 12pt; padding: 10px;'>{current_preview_message.replace(chr(10), '<br>')}</div>",
        background="white"
    )
    html_preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Estilo comum para os botões
    button_style = {
        "font": ("Helvetica", 10, "bold"),
        "width": 15,
        "height": 2,
        "borderwidth": 2,
        "relief": "raised"
    }
    
    # Frame para os botões
    button_frame = tk.Frame(main_container)
    button_frame.pack(pady=20, fill=tk.X)
    
    def aceitar_mensagem():
        """Aceita a mensagem e a coloca no prompt principal"""
        global current_message
        current_message = current_preview_message
        message_display.delete("1.0", tk.END)
        message_display.insert("1.0", current_message)
        start_button.config(state=tk.NORMAL)
        preview.destroy()
    
    def gerar_novamente():
        """Gera uma nova mensagem"""
        nonlocal current_preview_message
        current_preview_message = gerar_mensagem_pizza_mania("Cliente Teste")
        html_preview.set_html(
            f"<div style='font-family: \"Segoe UI Emoji\", sans-serif; font-size: 12pt; padding: 10px;'>{current_preview_message.replace(chr(10), '<br>')}</div>"
        )
    
    # Botões
    btn_aceitar = tk.Button(
        button_frame,
        text="Aceitar",
        command=aceitar_mensagem,
        bg="#4CAF50",  # Verde
        fg="white",
        **button_style
    )
    btn_aceitar.pack(side=tk.LEFT, expand=True, padx=5)
    
    btn_gerar = tk.Button(
        button_frame,
        text="Gerar Novamente",
        command=gerar_novamente,
        bg="#2196F3",  # Azul
        fg="white",
        **button_style
    )
    btn_gerar.pack(side=tk.LEFT, expand=True, padx=5)
    
    btn_fechar = tk.Button(
        button_frame,
        text="Fechar",
        command=preview.destroy,
        bg="#f44336",  # Vermelho
        fg="white",
        **button_style
    )
    btn_fechar.pack(side=tk.LEFT, expand=True, padx=5)
    
    # Centralizar janela
    preview.transient(root)
    preview.grab_set()
    preview.focus_force()
    
    # Posicionar no centro
    preview.update_idletasks()
    width = preview.winfo_width()
    height = preview.winfo_height()
    x = (preview.winfo_screenwidth() // 2) - (width // 2)
    y = (preview.winfo_screenheight() // 2) - (height // 2)
    preview.geometry(f'+{x}+{y}')

def check_whatsapp_login_status():
    """Verifica status do login do WhatsApp"""
    try:
        if os.path.exists(WHATSAPP_LOGIN_STATUS_FILE):
            with open(WHATSAPP_LOGIN_STATUS_FILE, 'r') as f:
                return json.load(f).get('logged_in', False)
        return False
    except:
        return False

def save_whatsapp_login_status(status):
    """Salva status do login do WhatsApp"""
    with open(WHATSAPP_LOGIN_STATUS_FILE, 'w') as f:
        json.dump({'logged_in': status}, f)

def wait_for_whatsapp_login(driver):
    """Aguarda login do WhatsApp verificando o campo de pesquisa"""
    try:
        driver.get("https://web.whatsapp.com/")
        
        # Aguarda página carregar
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # Aguarda elementos dinâmicos
        time.sleep(5)
        
        # Verifica se o campo de pesquisa está presente (indica que está logado)
        try:
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH, '//*[@id="side"]/div[1]/div/div[2]/div[2]/div/div/p'
                ))
            )
            if search_box.is_displayed():
                print("✅ WhatsApp Web está logado!")
                save_whatsapp_login_status(True)
                return True
        except:
            print("❌ WhatsApp Web NÃO está logado! Necessário escanear QR Code.")
            save_whatsapp_login_status(False)
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar login: {e}")
        save_whatsapp_login_status(False)
        return False

def send_whatsapp_message(driver, phone, message):
    """Envia mensagem individual via WhatsApp Web"""
    try:
        # URL codificada com número e mensagem
        encoded_message = requests.utils.quote(message)
        url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_message}"
        driver.get(url)
        
        # Aguarda carregamento da conversa
        message_box = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="textbox"]'))
        )
        
        # Aguarda mais um pouco para garantir que a página carregou completamente
        time.sleep(3)
        
        # Envia a mensagem
        try:
            # Primeiro, tenta enviar com ENTER
            time.sleep(1)
            
        
            # Se não enviou, tenta clicar no botão de enviar
            send_button = driver.find_element(By.CSS_SELECTOR, '#main > footer > div.x1n2onr6.xhtitgo.x9f619.x78zum5.x1q0g3np.xuk3077.x193iq5w.x122xwht.x1bmpntp.xs9asl8.x1swvt13.x1pi30zi.xnpuxes.copyable-area > div > span > div > div._ak1r > div.x123j3cw.xs9asl8.x9f619.x78zum5.x6s0dn4.xl56j7k.x1ofbdpd.x100vrsf.x1fns5xo > button > span')
            send_button.click()
            
        except:
            # Se ambos falharem, tenta um último método
            driver.execute_script("""
                document.querySelector('div[role="textbox"]').dispatchEvent(
                    new KeyboardEvent('keydown', {'key': 'Enter'})
                );
            """)
        
        # Aguarda confirmação de envio
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'span[data-icon="msg-check"], span[data-icon="msg-dblcheck"]'))
        )
        
        print(f"✅ Mensagem enviada para {phone}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar para {phone}: {e}")
        return False

def enviar_mensagens(contatos, mensagem_base):
    """Envia mensagens para lista de contatos"""
    global driver
    
    try:
        # Inicializa o driver em modo não-headless (normal)
        driver = initialize_driver(headless=False)
        if not driver:
            messagebox.showerror("Erro", "Não foi possível inicializar o navegador!")
            return
            
        # Verifica login - se não estiver logado, informa e interrompe o envio
        if not wait_for_whatsapp_login(driver):
            messagebox.showerror("Erro", "WhatsApp Web não está logado. Realize o login manualmente e tente novamente!")
            return
        
        mensagens_enviadas = 0
        hora_inicio = time.time()
        
        for index, row in contatos.iterrows():
            # Controle de taxa de envio
            if mensagens_enviadas >= MAX_MESSAGES_PER_HOUR:
                tempo_espera = 3600 - (time.time() - hora_inicio)
                if tempo_espera > 0:
                    time.sleep(tempo_espera)
                mensagens_enviadas = 0
                hora_inicio = time.time()

            # Pausa entre lotes
            if index > 0 and index % BATCH_SIZE == 0:
                time.sleep(300)

            # Preparar mensagem
            name = row["name"]
            phone = row["phone"]
            mensagem = mensagem_base.replace("%name%", name)
            
            # Enviar mensagem
            if send_whatsapp_message(driver, phone, mensagem):
                mensagens_enviadas += 1
            
            # Delay entre mensagens
            time.sleep(DELAY_BETWEEN_MESSAGES)
            
    except Exception as e:
        messagebox.showerror("Erro", f"Erro durante envio: {e}")
    finally:
        if driver:
            driver.quit()
            driver = None

def main():
    """Função principal"""
    global root, message_display, start_button, csv_file_path
    
    initialize_config()
    
    root = tk.Tk()
    root.title("Envio de Mensagens - Pizza Mania")
    root.geometry("800x600")
    
    frame_superior = tk.Frame(root)
    frame_superior.pack(pady=10, fill=tk.X)

    csv_file_path = tk.StringVar()

    csv_label = tk.Label(frame_superior, text="Arquivo CSV:")
    csv_label.grid(row=0, column=0, padx=5, pady=5)
    csv_entry = tk.Entry(frame_superior, textvariable=csv_file_path, width=50)
    csv_entry.grid(row=0, column=1, padx=5, pady=5)
    csv_button = tk.Button(frame_superior, text="Selecionar", 
                          command=lambda: csv_file_path.set(filedialog.askopenfilename()))
    csv_button.grid(row=0, column=2, padx=5, pady=5)

    message_frame = tk.Frame(root)
    message_frame.pack(pady=10, fill=tk.BOTH, expand=True)
    
    message_label = tk.Label(message_frame, text="Mensagem atual:")
    message_label.pack(anchor='w', padx=10)
    
    message_display = tk.Text(message_frame, height=6, wrap=tk.WORD)
    message_display.pack(fill=tk.BOTH, expand=True, padx=10)
    
    button_frame = tk.Frame(root)
    button_frame.pack(pady=5)
    
    generate_button = tk.Button(button_frame, text="Gerar Mensagem", 
                              command=mostrar_preview_mensagem)
    generate_button.pack(side=tk.LEFT, padx=5)
    
    start_button = tk.Button(button_frame, text="Iniciar Envio", 
                            command=lambda: threading.Thread(target=enviar_mensagens, args=(pd.read_csv(csv_file_path.get()), message_display.get("1.0", "end").strip()), daemon=True).start(), 
                            state=tk.DISABLED)
    start_button.pack(side=tk.LEFT, padx=5)

    def update_start_button(event=None):
        content = message_display.get("1.0", "end").strip()
        if content:
            start_button.config(state=tk.NORMAL)
        else:
            start_button.config(state=tk.DISABLED)
        message_display.edit_modified(False)
    
    message_display.bind("<<Modified>>", update_start_button)
    
    root.protocol("WM_DELETE_WINDOW", lambda: (driver.quit() if driver else None, root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    main()


