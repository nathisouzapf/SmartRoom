import time
import platform
import random
from threading import Thread
from flask import Flask, jsonify

# Tenta importar a biblioteca serial (pode não estar instalada ainda no seu PC)
try:
    import serial
    SERIAL_DISPONIVEL = True
except ImportError:
    SERIAL_DISPONIVEL = False

app = Flask(__name__)

# Configura a porta de acordo com o Sistema Operacional (visto em image_c1bd76.png que você usa Windows)
if platform.system() == "Windows":
    PORTA_SERIAL = 'COM3'  # Altere para a sua porta COM se espetar o Arduino no PC
else:
    PORTA_SERIAL = '/dev/ttyACM0'  # Padrão da Raspberry Pi

BAUD_RATE = 9600

# Dados iniciais/globais dos sensores
dados_sensores = {
    "presenca": 0,
    "luminosidade": 500,
    "ruido": 10,
    "ultima_atualizacao": "",
    "modo": "Simulação"
}

def ler_arduino():
    global dados_sensores
    
    # Se a biblioteca serial existir, tenta conectar ao hardware
    if SERIAL_DISPONIVEL:
        print(f"Tentando conectar na porta {PORTA_SERIAL}...")
        try:
            ser = serial.Serial(PORTA_SERIAL, BAUD_RATE, timeout=1)
            ser.flush()
            dados_sensores["modo"] = "Hardware Real"
            
            while True:
                if ser.in_waiting > 0:
                    linha = ser.readline().decode('utf-8').rstrip()
                    partes = linha.split(',')
                    if len(partes) == 3:
                        dados_sensores["presenca"] = int(partes[0])
                        dados_sensores["luminosidade"] = int(partes[1])
                        dados_sensores["ruido"] = int(partes[2])
                        dados_sensores["ultima_atualizacao"] = time.strftime("%H:%M:%S")
                time.sleep(0.1)
        except Exception as e:
            print(f"Não foi possível abrir a porta serial ({e}). Entrando em modo simulação.")
    
    # Caso não tenha Arduino conectado, gera dados falsos para testes no PC
    if dados_sensores["modo"] == "Simulação":
        print("Backend iniciado em modo de SIMULAÇÃO de dados.")
        while True:
            dados_sensores["presenca"] = random.choice([0, 1])
            dados_sensores["luminosidade"] = random.randint(200, 1000)
            dados_sensores["ruido"] = random.randint(5, 150)
            dados_sensores["ultima_atualizacao"] = time.strftime("%H:%M:%S")
            time.sleep(2)  # Atualiza a cada 2 segundos na simulação

@app.route('/api/sensores', methods=['GET'])
def obter_dados():
    return jsonify(dados_sensores)

if __name__ == '__main__':
    # Thread para ler os dados sem travar a API
    thread_leitura = Thread(target=ler_arduino)
    thread_leitura.daemon = True
    thread_leitura.start()
    
    # Roda o servidor local na porta 5000
    app.run(host='0.0.0.0', port=5000, debug=False)