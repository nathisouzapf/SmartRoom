# podemos excluir esse



import threading
import time
import random
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

# Estado inicial controlado do banco de dados fictício
salas_estado = {
    "Sala 01": {
        "status": "LIVRE", 
        "usuario": "", 
        "ra": "", 
        "horario": ""
    }
}

def simular_arduino():
    print("🤖 Modo Apresentação Ativado! Atualizando dados da Sala 01...")
    while True:
        try:
            # Sensores oscilando para dar dinamismo ao painel
            luminosidade = random.randint(450, 850)
            ruido = random.randint(15, 45)
            
            # Se já foi feito o clique de reserva, o status não volta a ser livre/ocupado
            status_atual = salas_estado["Sala 01"]["status"]

            # Envia a telemetria em tempo real para o navegador
            socketio.emit('atualizar_dados', {
                'status': status_atual,
                'luz': luminosidade,
                'ruido': ruido,
                'usuario': salas_estado["Sala 01"]["usuario"],
                'horario': salas_estado["Sala 01"]["horario"]
            })
            
            time.sleep(2) 
        except Exception as e:
            print(f"Erro na simulação: {e}")
            time.sleep(2)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('efetuar_reserva')
def tratar_reserva(dados):
    nome_sala = dados['sala']
    
    # Trava o estado interno do servidor como RESERVADO
    salas_estado[nome_sala]["status"] = "RESERVADO"
    salas_estado[nome_sala]["usuario"] = dados['nome']
    salas_estado[nome_sala]["ra"] = dados['ra']
    salas_estado[nome_sala]["horario"] = dados['horario']
    
    print(f"📌 [SALA RESERVADA] {nome_sala} por {dados['nome']} (RA: {dados['ra']})")
    
    # Devolve o comando imediato para atualizar a interface do usuário
    socketio.emit('reserva_confirmada_com_sucesso', {
        'sala': nome_sala,
        'status': "RESERVADO",
        'usuario': dados['nome'],
        'horario': dados['horario']
    })

if __name__ == '__main__':
    thread = threading.Thread(target=simular_arduino)
    thread.daemon = True
    thread.start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)