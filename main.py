import time
import platform
from threading import Thread
from flask import Flask, jsonify

# Tenta importar a biblioteca serial, 
try:
    import serial
    SERIAL_DISPONIVEL = True
except ImportError:
    SERIAL_DISPONIVEL = False

app = Flask(__name__)

# Configura a porta de acordo com o Sistema Operacional
if platform.system() == "Windows":
    PORTA_SERIAL = 'COM3'  
else:
    PORTA_SERIAL = '/dev/ttyACM0'  

BAUD_RATE = 9600

# Dados iniciais/globais dos sensores (Inicia com status de erro/desconectado)
dados_sensores = {
    "presenca": None,
    "luminosidade": None,
    "ruido": None,
    "ultima_atualizacao": "",
    "modo": "Desconectado",
    "erro": "Aguardando conexão com o hardware..."
}

def ler_arduino():
    global dados_sensores
    
    if not SERIAL_DISPONIVEL:
        dados_sensores["modo"] = "Erro"
        dados_sensores["erro"] = "Biblioteca 'pyserial' nao instalada no sistema."
        print("⚠️ ERRO: Biblioteca serial nao encontrada.")
        return # Encerra a função aqui, impedindo qualquer simulação

    print(f"Tentando conectar na porta {PORTA_SERIAL}...")
    try:
        ser = serial.Serial(PORTA_SERIAL, BAUD_RATE, timeout=1)
        ser.flush()
        
        # Se chegou aqui, conectou com sucesso! Limpa os erros.
        dados_sensores["modo"] = "Hardware Real"
        dados_sensores["erro"] = None 
        print("🔌 SUCESSO: Arduino conectado e operando em tempo real.")
        
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
        # Se falhar a abertura da porta física, aponta o erro diretamente na API
        dados_sensores["modo"] = "Erro"
        dados_sensores["erro"] = f"Nao foi possivel abrir a porta serial ({PORTA_SERIAL})."
        print(f"⚠️ ERRO DE HARDWARE: {dados_sensores['erro']}")
        # A função termina aqui. Sem loop de simulação secundário.

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