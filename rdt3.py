import time
import random
import socket
import os
import threading
import struct
import base64
import datetime

"""
RDT 3.0 (Reliable Data Transfer) usando UDP com simulação de latência, perda de pacotes e corrupção.

Esse script envia todos os arquivos da pasta origem para a pasta destino, modificando o nome do arquivo.
Implementei usando threads, ou seja, Sender e Receiver enviam logs no mesmo terminal. Por causa disso,
o terminal ficou um pouco poluído, portanto fiz os logs serem no estilo Wireshark para facilitar identificação.
"""

# Cores para os logs
BLUE = "\033[34m"  # Logs do sender
GREEN = "\033[32m" # Logs do receiver
RESET = "\033[0m"

# Pastas com os arquivos
SOURCE_DIR = "./Client"
DEST_DIR = "./Server"

# Estados do Remetente
WAIT_FOR_DATA = "WAIT_FOR_DATA"
WAIT_FOR_ACK0 = "WAIT_FOR_ACK0"
WAIT_FOR_ACK1 = "WAIT_FOR_ACK1"

# Estados do Receptor
WAIT_FOR_PKT0 = "WAIT_FOR_PKT0"
WAIT_FOR_PKT1 = "WAIT_FOR_PKT1"

# Tipos de pacotes
DATA_PKT = 0
ACK_PKT = 1

# Configurações de rede
SENDER_PORT = 5001
SENDER_ADDR = ('localhost', SENDER_PORT)
SENDER_TIMEOUT = 0.2

RECEIVER_PORT = 5000
RECEIVER_ADDR = ('localhost', RECEIVER_PORT)

# Probabilidade de erro
LOSS_PROB = 0.2
CORRUPT_PROB = 0.2

# Simulação de latência de rede (em segundos)
MIN_DELAY = 0.02
MAX_DELAY = 0.5

# Marcadores
END_OF_FILE_MARKER = "__EOF__"
END_OF_TRANSMISSION_MARKER = "__EOT__"

def calculate_checksum(data):
    """Calcula um checksum simples"""
    if isinstance(data, str):
        return sum(ord(c) for c in data) % 256
    elif isinstance(data, bytes):
        return sum(data) % 256
    return 0

def log_action(action, pkt_type, seq_num, is_corrupt=False, origin=None, dest=None, data_len=None):
    """Log estilo Wireshark"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    src = f"{origin[0]}:{origin[1]}" if origin else "Unknown"
    dst = f"{dest[0]}:{dest[1]}" if dest else "Unknown"
    
    type_str = "DATA" if pkt_type == DATA_PKT else "ACK"
    
    flags = []
    if seq_num is not None:
        flags.append(f"SEQ={seq_num}")
    if is_corrupt:
        flags.append("CORRUPT")
    if data_len is not None:
        flags.append(f"LEN={data_len}")
    
    flags_str = " [" + (", ".join(flags)) + "]" if flags else ""
    
    # Determina a cor com base na origem (sender ou receiver)
    color = BLUE if (origin == SENDER_ADDR or dest == SENDER_ADDR) else GREEN
    
    print(f"{color}{timestamp} {action.ljust(8)} ({src}) -> ({dst}) - {type_str}{flags_str}{RESET}")

def simulate_network_delay():
    """Simula um atraso de rede aleatório"""
    delay = random.uniform(MIN_DELAY, MAX_DELAY)
    time.sleep(delay)
    return delay

class RDTSender:
    def __init__(self):
        """Inicializa o remetente RDT"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(SENDER_ADDR)
        self.timeout = SENDER_TIMEOUT
        self.state = WAIT_FOR_DATA
        self.seq = 0
        self.last_pkt = None
        self.last_send_time = 0
        self.running = True
        print(f"{BLUE}---- SENDER criado - Estado inicial: {self.state} ----{RESET}")
    
    def make_pkt(self, seq, pkt_type, data):
        """Cria um pacote com os dados, tipo e sequência especificados"""
        # Serializa o pacote
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        checksum = calculate_checksum(data)
        
        # Formato do pacote: [tipo (1 byte), seq (1 byte), checksum (1 byte), tamanho (4 bytes), dados]
        header = struct.pack('!BBBi', pkt_type, seq, checksum, len(data))
        return header + data
    
    def send(self, data):
        """Envia dados usando protocolo rdt3.0"""
        if self.state != WAIT_FOR_DATA:
            print(f"{BLUE}ERRO: Tentativa de enviar dados enquanto em estado {self.state}{RESET}")
            return False

        # Cria um pacote com os dados
        packet = self.make_pkt(self.seq, DATA_PKT, data)
        self.last_pkt = packet
        
        # Simula perda de pacote
        if random.random() >= LOSS_PROB: 

            # Adiciona atraso de rede
            simulate_network_delay()

            # Simula corrupção de pacote
            if random.random() >= CORRUPT_PROB: 
                self.socket.sendto(packet, RECEIVER_ADDR)
                log_action("SENT", DATA_PKT, self.seq, False, SENDER_ADDR, RECEIVER_ADDR, len(data))
            else:
                corrupted_packet = self.make_pkt(self.seq, DATA_PKT, "CORRUPTED" + data)
                self.socket.sendto(corrupted_packet, RECEIVER_ADDR)
                log_action("SENT", DATA_PKT, self.seq, True, SENDER_ADDR, RECEIVER_ADDR, len(data))
        else:
            log_action("DROPPED", DATA_PKT, self.seq, False, SENDER_ADDR, RECEIVER_ADDR, len(data))
        
        # Atualiza o timestamp de último envio
        self.last_send_time = time.time()
        
        # Muda o estado para aguardar ACK
        if self.seq == 0:
            self.state = WAIT_FOR_ACK0
            print(f"{BLUE}============ SENDER: Transição para estado {self.state} (esperando ACK0){RESET}")
        else:
            self.state = WAIT_FOR_ACK1
            print(f"{BLUE}============ SENDER: Transição para estado {self.state} (esperando ACK1){RESET}")
        
        return True
    
    def receive_ack(self):
        """Tenta receber um ACK"""
        if self.state not in [WAIT_FOR_ACK0, WAIT_FOR_ACK1]:
            return False
        
        try:
            self.socket.settimeout(0.1)
            data, addr = self.socket.recvfrom(2048)
            
            # Adiciona atraso de rede
            simulate_network_delay()
            
            # Extrai o tipo de pacote, sequência e checksum
            pkt_type, seq, checksum, data_len = struct.unpack('!BBBi', data[:7])
            payload = data[7:]
            
            # Verifica se é um ACK
            if pkt_type != ACK_PKT:
                log_action("IGNORED", pkt_type, seq, False, addr, SENDER_ADDR)
                return False
            
            # Verifica se o checksum está correto
            if checksum != calculate_checksum(payload):
                log_action("RECEIVED", ACK_PKT, seq, True, addr, SENDER_ADDR)
                print(f"{BLUE}============ SENDER: ACK corrompido recebido, permanece em {self.state}{RESET}")
                return False
            
            log_action("RECEIVED", ACK_PKT, seq, False, addr, SENDER_ADDR)
            
            # Verifica se o ACK é para a sequência correta
            expected_seq = 0 if self.state == WAIT_FOR_ACK0 else 1
            if seq != expected_seq:
                print(f"{BLUE}============ SENDER: ACK{seq} inesperado recebido (esperando ACK{expected_seq}){RESET}")
                return False
            
            # ACK correto recebido, avança para próximo estado
            old_state = self.state
            self.state = WAIT_FOR_DATA
            self.seq = 1 - self.seq  # Alterna entre 0 e 1
            print(f"{BLUE}SENDER: ACK{seq} correto recebido, transição de {old_state} → {self.state} (próximo seq={self.seq}){RESET}")
            return True
            
        except socket.timeout:
            return False
        except Exception as e:
            print(f"{BLUE}============ SENDER: Erro ao receber ACK: {e}{RESET}")
            return False
        finally:
            # Reseta o timeout para não bloquear
            self.socket.settimeout(None)
    
    def check_timeout(self):
        """Verifica se houve timeout e retransmite se necessário"""
        if self.state in [WAIT_FOR_ACK0, WAIT_FOR_ACK1] and time.time() - self.last_send_time > self.timeout:
            seq_num = 0 if self.state == WAIT_FOR_ACK0 else 1
            print(f"{BLUE}============ SENDER: TIMEOUT detectado em {self.state}, retransmitindo pacote SEQ={seq_num}{RESET}")
            
            # Simula perda de pacote
            if random.random() >= LOSS_PROB:
                # Adiciona atraso de rede
                simulate_network_delay()
                
                # Simula corrupção de pacote
                if random.random() >= CORRUPT_PROB:
                    self.socket.sendto(self.last_pkt, RECEIVER_ADDR)
                    log_action("RESENT", DATA_PKT, self.seq, False, SENDER_ADDR, RECEIVER_ADDR)
                else:
                    corrupted_packet = self.last_pkt[0:7] + b"CORRUPTED"
                    self.socket.sendto(corrupted_packet, RECEIVER_ADDR)
                    log_action("RESENT", DATA_PKT, self.seq, True, SENDER_ADDR, RECEIVER_ADDR)
            else:
                log_action("DROPPED", DATA_PKT, self.seq, False, SENDER_ADDR, RECEIVER_ADDR)
            
            self.last_send_time = time.time()
            return True
        return False
    
    def close(self):
        """Fecha o socket"""
        self.running = False
        self.socket.close()
        print(f"{BLUE}============ SENDER: Socket fechado{RESET}")

class RDTReceiver:
    def __init__(self):
        """Inicializa o receptor RDT"""
        self.state = WAIT_FOR_PKT0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(RECEIVER_ADDR)
        self.running = True
        print(f"{GREEN}---- RECEIVER criado - Estado inicial: {self.state} ----{RESET}")
    
    def make_ack(self, seq):
        """Cria um ACK com a sequência especificada"""
        # ACKs são pequenos pacotes sem payload significativo
        dummy_payload = b"ACK"
        checksum = calculate_checksum(dummy_payload)
        
        # Formato do ACK: [tipo (1 byte), seq (1 byte), checksum (1 byte), tamanho (4 bytes), payload]
        header = struct.pack('!BBBi', ACK_PKT, seq, checksum, len(dummy_payload))
        return header + dummy_payload
    
    def unpack(self, packet):
        """Extrai informações de um pacote"""
        if len(packet) < 7:
            return None, None, None, None
        
        try:
            pkt_type, seq, checksum, data_len = struct.unpack('!BBBi', packet[:7])
            data = packet[7:]
            return pkt_type, seq, checksum, data
        except:
            return None, None, None, None
    
    def receive(self):
        """Recebe dados de acordo com o protocolo rdt3.0"""
        try:
            self.socket.settimeout(0.1)
            packet, addr = self.socket.recvfrom(4096)
            
            # Adiciona atraso de rede (sem imprimir)
            simulate_network_delay()
            
            pkt_type, seq, checksum, data = self.unpack(packet)
            
            if pkt_type is None:
                return None
                
            # Verifica o tipo do pacote
            if pkt_type != DATA_PKT:
                return None
                
            # Verifica se o checksum está correto
            is_corrupt = (checksum != calculate_checksum(data))
            
            # Log do pacote recebido
            log_action("RECEIVED", DATA_PKT, seq, is_corrupt, addr, RECEIVER_ADDR, len(data) if data else 0)
            
            # Processa de acordo com o estado
            if self.state == WAIT_FOR_PKT0:
                if not is_corrupt and seq == 0:
                    
                    # Pacote válido com seq=0
                    self.socket.sendto(self.make_ack(0), addr)
                    log_action("SENT", ACK_PKT, 0, False, RECEIVER_ADDR, addr)
                    
                    old_state = self.state
                    self.state = WAIT_FOR_PKT1
                    print(f"{GREEN}============ RECEIVER: Transição de {old_state} → {self.state} (recebido pacote seq=0){RESET}")
                    
                    # Converte bytes para string se necessário
                    if isinstance(data, bytes):
                        try:
                            data = data.decode('utf-8')
                        except UnicodeDecodeError:
                            pass  # Mantém como bytes se não puder decodificar
                    
                    return data
                else:
                    # Pacote corrompido ou com seq incorreta, envia ACK para última seq válida
                    self.socket.sendto(self.make_ack(1), addr)
                    log_action("SENT", ACK_PKT, 1, False, RECEIVER_ADDR, addr)
                    print(f"{GREEN}============ RECEIVER: Permanece em {self.state} (recebido pacote inválido){RESET}")
            
            elif self.state == WAIT_FOR_PKT1:
                if not is_corrupt and seq == 1:
                    
                    # Pacote válido com seq=1
                    self.socket.sendto(self.make_ack(1), addr)
                    log_action("SENT", ACK_PKT, 1, False, RECEIVER_ADDR, addr)
                    
                    old_state = self.state
                    self.state = WAIT_FOR_PKT0
                    print(f"{GREEN}============ RECEIVER: Transição de {old_state} → {self.state} (recebido pacote seq=1){RESET}")
                    
                    # Converte bytes para string se necessário
                    if isinstance(data, bytes):
                        try:
                            data = data.decode('utf-8')
                        except UnicodeDecodeError:
                            pass  # Mantém como bytes se não puder decodificar
                    
                    return data
                else:
                    # Pacote corrompido ou com seq incorreta, envia ACK para última seq válida
                    self.socket.sendto(self.make_ack(0), addr)
                    log_action("SENT", ACK_PKT, 0, False, RECEIVER_ADDR, addr)
                    print(f"{GREEN}============ RECEIVER: Permanece em {self.state} (recebido pacote inválido){RESET}")
            
        except socket.timeout:
            pass
        except Exception as e:
            print(f"{GREEN}Erro ao receber pacote: {e}{RESET}")
        finally:
            self.socket.settimeout(None)
        
        return None
    
    def close(self):
        """Fecha o socket"""
        self.running = False
        self.socket.close()
        print(f"{GREEN}============ RECEIVER: Socket fechado{RESET}")

def sender_thread():
    # Garante que o diretório existe
    client_dir = SOURCE_DIR
    if not os.path.exists(client_dir):
        os.makedirs(client_dir)
    
    # Lista todos os arquivos no diretório Client
    files = [f for f in os.listdir(client_dir) if os.path.isfile(os.path.join(client_dir, f))]
    
    if not files:
        print(f"{BLUE}Nenhum arquivo encontrado na pasta{RESET}")
        return
    
    print(f"{BLUE}Encontrados {len(files)} arquivos para transferir{RESET}")
    
    # Configura o remetente
    sender = RDTSender()
    
    # Transfere cada arquivo
    for filename in files:
        filepath = os.path.join(client_dir, filename)
        
        print(f"{BLUE}============ SENDER: Iniciando transferência: '{filename}'{RESET}")
        
        # Envia o nome do arquivo de destino
        sender.send(filename)
        while sender.state != WAIT_FOR_DATA:
            sender.check_timeout()
            sender.receive_ack()
            time.sleep(0.1)
        
        # Envia o arquivo
        with open(filepath, 'rb') as f:
            while True:
                # Lê em chunks de 1KB
                chunk = f.read(1024)  
                if not chunk:
                    break
                    
                # Lógica de corrupção fake precisa receber string
                data = base64.b64encode(chunk).decode('utf-8')
                
                # Envia um chunk do arquivo
                sender.send(data)
                while sender.state != WAIT_FOR_DATA:
                    # Espera confirmação antes de enviar o próximo chunk
                    sender.check_timeout()
                    sender.receive_ack()
                    time.sleep(0.1)
        
        # Envia marcador de fim de arquivo
        sender.send(END_OF_FILE_MARKER) 
        while sender.state != WAIT_FOR_DATA:
            sender.check_timeout()
            sender.receive_ack()
            time.sleep(0.1)
        
        print(f"{BLUE}============ SENDER: '{filename}' enviado com sucesso{RESET}")
    
    # Envia marcador de fim de transmissão
    sender.send(END_OF_TRANSMISSION_MARKER) 
    while sender.state != WAIT_FOR_DATA:
        sender.check_timeout()
        sender.receive_ack()
        time.sleep(0.1)
    
    print(f"{BLUE}============ SENDER: Todos os {len(files)} arquivos foram enviados com sucesso{RESET}")
    sender.close()

def receiver_thread():
    # Garante que o diretório existe
    server_dir = DEST_DIR
    if not os.path.exists(server_dir):
        os.makedirs(server_dir)
    
    # Configura o receptor
    receiver = RDTReceiver()
    
    print(f"{GREEN}Esperando por arquivos...{RESET}")
    
    # Recebe cada arquivo
    while receiver.running:

        # Recebe o nome do arquivo
        filename = None
        while filename is None and receiver.running:
            filename = receiver.receive()
            time.sleep(0.1)
        
        # Verifica se é o sinal de fim de transmissão
        if filename == END_OF_TRANSMISSION_MARKER:
            print(f"{GREEN}============ RECEIVER: Recebido sinal de fim de transmissão. Transferência completa.{RESET}")
            break
        
        print(f"{GREEN}============ RECEIVER: Recebendo arquivo com nome: {filename}{RESET}")

        # Renomeia o arquivo no destino para <nome>_received
        filename_appended = os.path.splitext(filename)[0] + "_received" + os.path.splitext(filename)[1]
        destination = os.path.join(server_dir, filename_appended)
        
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, 'wb') as f:
            while receiver.running:
                # Recebe um chunk de dados
                data = None
                while data is None and receiver.running:
                    data = receiver.receive()
                    time.sleep(0.1)
                    
                # Verifica se é o final do arquivo
                if data == END_OF_FILE_MARKER:
                    break
                    
                # Escreve chunk no arquivo
                chunk = base64.b64decode(data)
                f.write(chunk)
        
        print(f"{GREEN}============ RECEIVER: Arquivo {filename} recebido com sucesso e salvo em {destination}{RESET}")
    
    receiver.close()

def main():
    """Executa o receptor e emissor em threads separadas"""

    # Receiver como daemon para encerrar junto com a main
    recv_thread = threading.Thread(target=receiver_thread, daemon=True) 
    recv_thread.start()

    time.sleep(1)

    send_thread = threading.Thread(target=sender_thread)
    send_thread.start()

    recv_thread.join()
    send_thread.join()
    
if __name__ == "__main__":
    main()
