import threading # Biblioteca que aplica múltiplas threads - permite ler o cabo USB sem travar o site
import time 
from datetime import datetime, timedelta 
import serial # Realiza a comunicação entre o Arduino e o Python 
from flask import Flask, render_template # Framework que disponibiliza o servidor HTTP e serve a interface aos usuários
from flask_socketio import SocketIO # Permite conexão em tempo real entre web e Python

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

# --- 🔌 CONFIGURAÇÃO DA PORTA USB ---
PORTA_ARDUINO = 'COM3'

try:
    arduino = serial.Serial(PORTA_ARDUINO, 9600, timeout=1)
    time.sleep(2) # Aguarda o reset da placa
    print(f"🔌 [SUCESSO] Conectado ao Arduino na porta {PORTA_ARDUINO}!")
except Exception as e:
    arduino = None
    print(f"⚠️ [ERRO] Não foi possível conectar na porta {PORTA_ARDUINO}. Erro: {e}")

# Dicionários que salvam os dados na RAM
# Gerencia quem reservou a sala
salas_estado = {
    "Sala 01": {
        "status": "LIVRE", 
        "usuario": "", 
        "ra": "", 
        "horario": ""
    }
}

# Guarda na RAM a leitura dos pinos do Arduino
dados_sensores_globais = {
    "presenca": 0,
    "luminosidade": 500,
    "ruido": 30
}

def ler_dados_arduino():
    global dados_sensores_globais
    print("🤖 Processamento de dados reais do Arduino ativado...")
    
    # Manter os valores persistentes FORA do loop para evitar que resetem sozinhos
    presenca_sensor = 0
    luminosidade = 500
    ruido = 30

    while True:
        try:
            status_atual = salas_estado["Sala 01"]["status"]
            horario_exibicao = salas_estado["Sala 01"]["horario"]

            # 1. LEITURA DOS DADOS REAIS DO ARDUINO
            if arduino and arduino.in_waiting > 0:
                linha = arduino.readline().decode('utf-8', errors='ignore').strip()
                dados_separados = linha.split(',')
                
                if len(dados_separados) == 3:
                    presenca_sensor = int(dados_separados[0])
                    luminosidade = int(dados_separados[1])
                    ruido = int(dados_separados[2])
                    
                    # PRINT PARA VER OS DADOS NO TERMINAL DO VS CODE:
                    print(f"📊 [VS CODE] Presença: {presenca_sensor} | Luz: {luminosidade} | Ruído: {ruido} | Status: {status_atual}")

                    # Atualiza o cache global para consulta da API externa
                    dados_sensores_globais["presenca"] = presenca_sensor
                    dados_sensores_globais["luminosidade"] = luminosidade
                    dados_sensores_globais["ruido"] = ruido

            # 2. LÓGICA DE DETECÇÃO AUTOMÁTICA (Se não estiver reservada via site)
            if status_atual != "RESERVADO":
                if presenca_sensor == 1:
                    status_atual = "OCUPADO"
                    agora = datetime.now()
                    hora_atual_cheia = agora.replace(minute=0, second=0, microsecond=0)
                    hora_liberacao = hora_atual_cheia + timedelta(hours=1)
                    horario_exibicao = f"{hora_atual_cheia.strftime('%H:%M')} - {hora_liberacao.strftime('%H:%M')}"
                else:
                    status_atual = "LIVRE"
                    horario_exibicao = ""
                
                # Atualiza o estado global da sala
                salas_estado["Sala 01"]["status"] = status_atual
                salas_estado["Sala 01"]["horario"] = horario_exibicao

          ## 3. ENVIA COMANDO DE VOLTA PARA O ARDUINO (LED E LCD)
            if arduino:
                # Presença detectada (1) E luminosidade abaixo de 901 (Luz Forte, Ideal ou Fraca)
                if presenca_sensor == 1 and luminosidade < 901:
                    arduino.write(b'1')  # Manda comando '1' para acender o LED no pino 8
                
                # Mantém a verificação se a sala foi reservada via site para o LCD
                elif status_atual == "RESERVADO":
                    arduino.write(b'2')  # Escreve RESERVADA no LCD
                
                # Se estiver no Escuro Total (>= 901) ou se não houver presença (0), o LED desliga
                else:
                    arduino.write(b'0')  # Manda comando '0' para apagar o LED

            # 4. DISPARA TELEMETRIA ESTÁVEL PARA A PÁGINA WEB A CADA 0.2 SEGUNDOS
            socketio.emit('atualizar_dados', {
                'status': status_atual,
                'luz': luminosidade,
                'ruido': ruido,
                'presenca': presenca_sensor,
                'usuario': salas_estado["Sala 01"]["usuario"],
                'horario': horario_exibicao
            })
            
            time.sleep(0.2) # Delay estável de leitura
        except Exception as e:
            print(f"Erro no processamento do Arduino: {e}")
            time.sleep(1)

@app.route('/')
def index():
    return render_template('index.html')

# --- 📊 ROTA DA API PARA ACOMPANHAMENTO DE DADOS EM TEMPO REAL ---
@app.route('/api/sensores')
def obter_dados_api():
    return {
        "status_sala": salas_estado["Sala 01"]["status"],
        "horario_reserva": salas_estado["Sala 01"]["horario"],
        "usuario_reserva": salas_estado["Sala 01"]["usuario"],
        "sensor_presenca": dados_sensores_globais["presenca"],
        "sensor_luminosidade": dados_sensores_globais["luminosidade"],
        "sensor_ruido": dados_sensores_globais["ruido"]
    }

@socketio.on('efetuar_reserva')
def tratar_reserva(dados):
    nome_sala = dados['sala']
    salas_estado[nome_sala]["status"] = "RESERVADO"
    salas_estado[nome_sala]["usuario"] = dados['nome']
    salas_estado[nome_sala]["ra"] = dados['ra']
    salas_estado[nome_sala]["horario"] = dados['horario']
    
    print(f"📌 [SALA RESERVADA VIA WEB] {nome_sala} por {dados['nome']}")
    
    socketio.emit('reserva_confirmada_com_sucesso', {
        'sala': nome_sala,
        'status': "RESERVADO",
        'usuario': dados['nome'],
        'horario': dados['horario']
    })

@socketio.on('cancelar_reserva')
def tratar_cancelamento():
    salas_estado["Sala 01"]["status"] = "LIVRE"
    salas_estado["Sala 01"]["usuario"] = ""
    salas_estado["Sala 01"]["ra"] = ""
    salas_estado["Sala 01"]["horario"] = ""
    
    print("🔓 [SALA LIBERADA VIA WEB] Sala 01 foi liberada.")
    
    socketio.emit('reserva_cancelada_com_sucesso', {
        'sala': "Sala 01",
        'status': "LIVRE"
    })

if __name__ == '__main__':
    thread = threading.Thread(target=ler_dados_arduino)
    thread.daemon = True
    thread.start()
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)