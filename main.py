# podemos excluir esse

import time
import platform
from threading import Thread
from flask import Flask, jsonify

# Tenta importar a biblioteca serial
try:
    import serial
    SERIAL_DISPONIVEL = True
except ImportError:
    SERIAL_DISPONIVEL = False

app = Flask(__name__)

# Configura a porta de acordo com o Sistema Operacional
if platform.system() == "Windows":
    PORTA_SERIAL = "COM3"
else:
    PORTA_SERIAL = "/dev/ttyACM0"

BAUD_RATE = 9600

# Dados dos sensores
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
        dados_sensores["erro"] = "Biblioteca pyserial nao instalada."
        print("⚠️ ERRO: Biblioteca serial nao encontrada.")
        return

    print(f"Tentando conectar na porta {PORTA_SERIAL}...")

    try:
        ser = serial.Serial(PORTA_SERIAL, BAUD_RATE, timeout=1)
        ser.flush()

        dados_sensores["modo"] = "Hardware Real"
        dados_sensores["erro"] = None

        print("🔌 SUCESSO: Arduino conectado e operando em tempo real.")

        while True:
            if ser.in_waiting > 0:
                linha = ser.readline().decode("utf-8").rstrip()

                print(f"Recebido: {linha}")

                partes = linha.split(",")

                if len(partes) == 3:
                    dados_sensores["presenca"] = int(partes[0])
                    dados_sensores["luminosidade"] = int(partes[1])
                    dados_sensores["ruido"] = int(partes[2])
                    dados_sensores["ultima_atualizacao"] = time.strftime("%H:%M:%S")

            time.sleep(0.1)

    except Exception as e:
        dados_sensores["modo"] = "Erro"
        dados_sensores["erro"] = str(e)

        print(f"⚠️ ERRO DE HARDWARE: {e}")


# Página inicial
@app.route("/")
def home():
    return f"""
    <html>
    <head>
        <title>SmartRoom</title>
        <meta http-equiv="refresh" content="2">
    </head>
    <body>
        <h1>🏠 SmartRoom</h1>

        <p><strong>Modo:</strong> {dados_sensores['modo']}</p>
        <p><strong>Presença:</strong> {dados_sensores['presenca']}</p>
        <p><strong>Luminosidade:</strong> {dados_sensores['luminosidade']}</p>
        <p><strong>Ruído:</strong> {dados_sensores['ruido']}</p>
        <p><strong>Última atualização:</strong> {dados_sensores['ultima_atualizacao']}</p>
        <p><strong>Erro:</strong> {dados_sensores['erro']}</p>

        <hr>

        <a href="/api/sensores">Ver JSON da API</a>
    </body>
    </html>
    """


# API
@app.route("/api/sensores", methods=["GET"])
def obter_dados():
    return jsonify(dados_sensores)


if __name__ == "__main__":
    thread_leitura = Thread(target=ler_arduino)
    thread_leitura.daemon = True
    thread_leitura.start()

    app.run(host="0.0.0.0", port=5000, debug=False)