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

# Define the log file for Wireshark-style logs
LOG_FILE = "network_logs.txt"

def calculate_checksum(data):
    """Calcula um checksum simples"""
    if isinstance(data, str):
        return sum(ord(c) for c in data) % 256
    elif isinstance(data, bytes):
        return sum(data) % 256
    return 0

def log_action(action, pkt_type, seq_num, origin=None, dest=None, data_len=None):
    """Log estilo Wireshark"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    src = f"{origin[0]}:{origin[1]}" if origin else "Unknown"
    dst = f"{dest[0]}:{dest[1]}" if dest else "Unknown"
    
    type_str = "DATA" if pkt_type == DATA_PKT else "ACK"
    
    flags = []
    if seq_num is not None:
        flags.append(f"SEQ={seq_num}")
    if data_len is not None:
        flags.append(f"LEN={data_len}")
    
    flags_str = " [" + (", ".join(flags)) + "]" if flags else ""
    
    log_message = f"{timestamp} {action.ljust(8)} ({src}) -> ({dst}) - {type_str}{flags_str}\n"
    
    # Write the log message to the log file
    with open(LOG_FILE, "a") as log_file:
        log_file.write(log_message)

class Network:
    """Simula uma rede com latência, perda de pacotes e corrupção"""
    def __init__(self, loss_prob=LOSS_PROB, corrupt_prob=CORRUPT_PROB, min_delay=MIN_DELAY, max_delay=MAX_DELAY):
        self.loss_prob = loss_prob
        self.corrupt_prob = corrupt_prob
        self.min_delay = min_delay
        self.max_delay = max_delay
        
        # Cria os sockets para o remetente e receptor
        self.sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sender_socket.bind(SENDER_ADDR)
        
        self.receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiver_socket.bind(RECEIVER_ADDR)
        
        # Cache para último endereço de origem
        self.last_sender_addr = None
        self.last_receiver_addr = None
    
    def _extract_packet_info(self, packet):
        """Extrai informações básicas do pacote para log"""
        if len(packet) < 7:
            return None, None, None
            
        pkt_type, seq, _, data_len = struct.unpack('!BBBi', packet[:7])
        return pkt_type, seq, data_len
    
    def _simulate_delay(self):
        """Simula um atraso de rede aleatório"""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)
        return delay
    
    def _corrupt_packet(self, packet):
        """Corrompe um pacote modificando seu conteúdo"""
        if len(packet) < 7:
            return packet
            
        header = packet[:7]
        payload = packet[7:]
        
        # Corrompe aproximadamente metade do payload
        payload_bytearray = bytearray(payload)
        indices = random.sample(range(len(payload_bytearray)), len(payload_bytearray) // 2)
        for index in indices:
            payload_bytearray[index] ^= 0xFF  # Inverte os bits dos bytes selecionados
        corrupted_payload = bytes(payload_bytearray)
        
        return header + corrupted_payload
    
    def sender_send(self, packet):
        """Envia um pacote do remetente para o receptor"""
        # Extrai informações para log
        pkt_type, seq, data_len = self._extract_packet_info(packet)
            
        # Simula perda de pacote
        if random.random() < self.loss_prob:
            log_action("DROPPED", pkt_type, seq, SENDER_ADDR, RECEIVER_ADDR, data_len)
            return
            
        # Simula atraso de rede
        self._simulate_delay()
        
        # Simula corrupção de pacote
        is_corrupt = random.random() < self.corrupt_prob
        if is_corrupt:
            packet = self._corrupt_packet(packet)
            
        # Envia o pacote para o receptor
        self.sender_socket.sendto(packet, RECEIVER_ADDR)
        log_action("SENT", pkt_type, seq, SENDER_ADDR, RECEIVER_ADDR, data_len)
    
    def receiver_send(self, packet):
        """Envia um pacote do receptor para o remetente"""
        # Extrai informações para log
        pkt_type, seq, data_len = self._extract_packet_info(packet)
        
        # Verifica se temos o endereço do remetente registrado
        if not self.last_sender_addr:
            print(f"{GREEN}Erro: Tentativa de enviar ACK sem conhecer o endereço do remetente{RESET}")
            return

        # Simula perda de pacote
        if random.random() < self.loss_prob:
            log_action("DROPPED", pkt_type, seq, RECEIVER_ADDR, self.last_sender_addr, data_len)
            return
            
        # Simula atraso de rede
        self._simulate_delay()
        
        # Simula corrupção de pacote
        is_corrupt = random.random() < self.corrupt_prob
        if is_corrupt:
            packet = self._corrupt_packet(packet)
            
        # Envia o pacote para o remetente
        self.receiver_socket.sendto(packet, self.last_sender_addr)
        log_action("SENT", pkt_type, seq, RECEIVER_ADDR, self.last_sender_addr, data_len)
    
    def sender_receive(self, timeout=None):
        """Recebe dados para o remetente (ACKs)"""
        if timeout:
            self.sender_socket.settimeout(timeout)
        
        try:
            data, addr = self.sender_socket.recvfrom(2048)
            self.last_receiver_addr = addr
            
            # Simula atraso de rede
            self._simulate_delay()
            
            # Extrai informações para log
            pkt_type, seq, data_len = self._extract_packet_info(data)
            log_action("RECEIVED", pkt_type, seq, addr, SENDER_ADDR, data_len)
            
            return data, addr
            
        except socket.timeout:
            raise
        except Exception as e:
            print(f"{BLUE}Erro na rede ao receber: {e}{RESET}")
            raise
        finally:
            if timeout:
                self.sender_socket.settimeout(None)
    
    def receiver_receive(self, timeout=None):
        """Recebe dados para o receptor (pacotes de dados)"""
        if timeout:
            self.receiver_socket.settimeout(timeout)
        
        try:
            data, addr = self.receiver_socket.recvfrom(4096)
            self.last_sender_addr = addr
            
            # Simula atraso de rede
            self._simulate_delay()
            
            # Extrai informações para log
            pkt_type, seq, data_len = self._extract_packet_info(data)
            log_action("RECEIVED", pkt_type, seq, addr, RECEIVER_ADDR, data_len)
            
            return data, addr
            
        except socket.timeout:
            raise
        except Exception as e:
            print(f"{GREEN}Erro na rede ao receber: {e}{RESET}")
            raise
        finally:
            if timeout:
                self.receiver_socket.settimeout(None)
    
    def close(self):
        """Fecha os sockets da rede"""
        self.sender_socket.close()
        self.receiver_socket.close()
        print("---- Network: Sockets fechados ----")

class RDTSender:
    def __init__(self, network):
        """Inicializa o remetente RDT"""
        self.timeout = SENDER_TIMEOUT
        self.state = WAIT_FOR_DATA
        self.seq = 0
        self.last_pkt = None
        self.last_send_time = 0
        self.network = network
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
            print(f"{BLUE}SENDER: ERRO - Tentativa de enviar dados enquanto em estado {self.state}{RESET}")
            return False

        # Cria um pacote com os dados
        packet = self.make_pkt(self.seq, DATA_PKT, data)
        self.last_pkt = packet
        
        # Envia através da rede simulada
        self.network.sender_send(packet)
        
        # Atualiza o timestamp de último envio
        self.last_send_time = time.time()
        
        # Muda o estado para aguardar ACK
        if self.seq == 0:
            self.state = WAIT_FOR_ACK0
            print(f"{BLUE}SENDER: Transição para estado {self.state} (esperando ACK0){RESET}")
        else:
            self.state = WAIT_FOR_ACK1
            print(f"{BLUE}SENDER: Transição para estado {self.state} (esperando ACK1){RESET}")
        
        return True
    
    def receive_ack(self):
        """Tenta receber um ACK"""
        if self.state not in [WAIT_FOR_ACK0, WAIT_FOR_ACK1]:
            return False
        
        try:
            data, addr = self.network.sender_receive(0.1)
            
            # Extrai o tipo de pacote, sequência e checksum
            pkt_type, seq, checksum, data_len = struct.unpack('!BBBi', data[:7])
            payload = data[7:]
            
            # Verifica se é um ACK
            if pkt_type != ACK_PKT:
                print(f"{BLUE}SENDER: ERRO - Pacote não-ACK recebido{RESET}")
                return False
            
            # Verifica se o checksum está correto
            if checksum != calculate_checksum(payload):
                print(f"{BLUE}SENDER: ACK corrompido recebido, permanece em {self.state}{RESET}")
                return False
            
            expected_seq = 0 if self.state == WAIT_FOR_ACK0 else 1
            
            # Se receber o ACK esperado
            if seq == expected_seq:
                # ACK correto recebido, avança para próximo estado
                old_state = self.state
                self.state = WAIT_FOR_DATA
                self.seq = 1 - self.seq  # Alterna entre 0 e 1
                print(f"{BLUE}SENDER: ACK{seq} correto recebido, transição de {old_state} → {self.state} (próximo seq={self.seq}){RESET}")
                return True
            else:
                # Ignora ACKs não esperados (duplicados ou incorretos)
                print(f"{BLUE}SENDER: ACK{seq} inesperado recebido (esperando ACK{expected_seq}), ignorado{RESET}")
                return False
                
        except socket.timeout:
            return False
        except Exception as e:
            print(f"{BLUE}SENDER: ERRO ao receber ACK: {e}{RESET}")
            return False
    
    def check_timeout(self):
        """Verifica se houve timeout e retransmite se necessário"""
        if self.state in [WAIT_FOR_ACK0, WAIT_FOR_ACK1] and time.time() - self.last_send_time > self.timeout:
            seq_num = 0 if self.state == WAIT_FOR_ACK0 else 1
            print(f"{BLUE}SENDER: TIMEOUT detectado em {self.state}, retransmitindo pacote SEQ={seq_num}{RESET}")
            
            # Envia através da rede simulada
            self.network.sender_send(self.last_pkt)
            
            self.last_send_time = time.time()
            return True
        return False
    
    def close(self):
        """Encerra o remetente"""
        print(f"{BLUE}---- SENDER Encerrado ----{RESET}")

class RDTReceiver:
    def __init__(self, network, running_flag=None):
        """Inicializa o receptor RDT"""
        self.state = WAIT_FOR_PKT0
        self.network = network
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
            packet, addr = self.network.receiver_receive(0.1)
            
            pkt_type, seq, checksum, data = self.unpack(packet)
            
            if pkt_type is None:
                return None
                
            # Verifica o tipo do pacote
            if pkt_type != DATA_PKT:
                return None
                
            # Verifica se o checksum está correto
            is_corrupt = (checksum != calculate_checksum(data))
            
            # Processa de acordo com o estado
            if self.state == WAIT_FOR_PKT0:
                if not is_corrupt and seq == 0:
                    # Pacote válido com seq=0, processamos e mudamos de estado
                    ack_packet = self.make_ack(0)
                    self.network.receiver_send(ack_packet)
                    
                    old_state = self.state
                    self.state = WAIT_FOR_PKT1
                    print(f"{GREEN}RECEIVER: Transição de {old_state} → {self.state} (recebido pacote seq=0){RESET}")
                    
                    return data  # Retorna os dados diretamente como bytes
                else:
                    # Pacote corrompido ou com seq=1 quando esperávamos seq=0
                    # Reenviamos ACK para o último pacote recebido com sucesso (seq=1)
                    ack_packet = self.make_ack(1)
                    self.network.receiver_send(ack_packet)
                    if is_corrupt:
                        print(f"{GREEN}RECEIVER: Permanece em {self.state} (recebido pacote corrompido){RESET}")
                    else:
                        print(f"{GREEN}RECEIVER: Permanece em {self.state} (recebido pacote com seq incorreta){RESET}")
            
            elif self.state == WAIT_FOR_PKT1:
                if not is_corrupt and seq == 1:
                    # Pacote válido com seq=1, processamos e mudamos de estado
                    ack_packet = self.make_ack(1)
                    self.network.receiver_send(ack_packet)
                    
                    old_state = self.state
                    self.state = WAIT_FOR_PKT0
                    print(f"{GREEN}RECEIVER: Transição de {old_state} → {self.state} (recebido pacote seq=1){RESET}")
                    
                    return data  # Retorna os dados diretamente como bytes
                else:
                    # Pacote corrompido ou com seq=0 quando esperávamos seq=1
                    # Reenviamos ACK para o último pacote recebido com sucesso (seq=0)
                    ack_packet = self.make_ack(0)
                    self.network.receiver_send(ack_packet)
                    if is_corrupt:
                        print(f"{GREEN}RECEIVER: Permanece em {self.state} (recebido pacote corrompido){RESET}")
                    else:
                        print(f"{GREEN}RECEIVER: Permanece em {self.state} (recebido pacote com seq incorreta){RESET}")
            
        except socket.timeout:
            pass
        except Exception as e:
            print(f"{GREEN}RECEIVER: ERRO ao receber pacote: {e}{RESET}")
        
        return None
    
    def close(self):
        """Encerra o receptor"""
        print(f"{GREEN}---- RECEIVER Encerrado ----{RESET}")

def sender_thread(network, running_flag):
    # Garante que o diretório existe
    client_dir = SOURCE_DIR
    if not os.path.exists(client_dir):
        os.makedirs(client_dir)
    
    # Lista todos os arquivos no diretório Client
    files = [f for f in os.listdir(client_dir) if os.path.isfile(os.path.join(client_dir, f))]
    
    if not files:
        print(f"{BLUE}============ SENDER: Nenhum arquivo encontrado na pasta{RESET}")
        return
    
    print(f"{BLUE}============ SENDER: Encontrados {len(files)} arquivos para transferir{RESET}")
    
    # Configura o remetente
    sender = RDTSender(network)
    
    # Transfere cada arquivo
    for filename in files:
        
        filepath = os.path.join(client_dir, filename)
        
        print(f"{BLUE}============ SENDER: Iniciando transferência: '{filename}'{RESET}")
        
        # Envia o nome do arquivo de destino
        sender.send(filename.encode('utf-8'))
        while sender.state != WAIT_FOR_DATA:
            sender.check_timeout()
            sender.receive_ack()
        
        # Envia o arquivo
        with open(filepath, 'rb') as f:
            while True and running_flag.is_set():
                    
                # Lê em chunks de 1KB
                chunk = f.read(1024)  
                if not chunk:
                    break
                    
                # Envia o chunk do arquivo diretamente como bytes
                sender.send(chunk)
                while sender.state != WAIT_FOR_DATA:
                    sender.check_timeout()
                    sender.receive_ack()  
            
        # Envia marcador de fim de arquivo
        sender.send(END_OF_FILE_MARKER.encode('utf-8')) 
        while sender.state != WAIT_FOR_DATA:
            sender.check_timeout()
            sender.receive_ack()
        
        print(f"{BLUE}============ SENDER: '{filename}' enviado com sucesso{RESET}")
    
    # Envia marcador de fim de transmissão
    sender.send(END_OF_TRANSMISSION_MARKER.encode('utf-8')) 
    while sender.state != WAIT_FOR_DATA:
        sender.check_timeout()
        sender.receive_ack()
        time.sleep(0.1)
    
    print(f"{BLUE}============ SENDER: Todos os {len(files)} arquivos foram enviados com sucesso{RESET}")
    sender.close()

def receiver_thread(network, running_flag):
    # Garante que o diretório existe
    server_dir = DEST_DIR
    if not os.path.exists(server_dir):
        os.makedirs(server_dir)
    
    # Configura o receptor
    receiver = RDTReceiver(network)
    
    print(f"{GREEN}============ RECEIVER: Esperando por arquivos...{RESET}")
    
    # Recebe cada arquivo
    while True:
        # Recebe o nome do arquivo
        filename = None
        while filename is None:
            filename = receiver.receive()
        
        # Verifica se é o sinal de fim de transmissão
        if filename == END_OF_TRANSMISSION_MARKER.encode('utf-8'):
            print(f"{GREEN}============ RECEIVER: Recebido sinal de fim de transmissão. Transferência completa.{RESET}")
            break
        
        filename = filename.decode('utf-8')
        print(f"{GREEN}============ RECEIVER: Recebendo arquivo com nome: {filename}{RESET}")

        # Renomeia o arquivo no destino para <nome>_received
        filename_appended = os.path.splitext(filename)[0] + "_received" + os.path.splitext(filename)[1]
        destination = os.path.join(server_dir, filename_appended)
        
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        with open(destination, 'wb') as f:
            while running_flag.is_set():  # Check flag at the start of each chunk receipt
                # Recebe um chunk de dados
                data = None
                while data is None:
                    data = receiver.receive()
                    
                if not running_flag.is_set() or data is None:
                    break
                    
                # Verifica se é o final do arquivo
                if data == END_OF_FILE_MARKER.encode('utf-8'):
                    break
                    
                # Escreve chunk no arquivo
                try:
                    f.write(data)  # Escreve diretamente os bytes recebidos
                except Exception as e:
                    print(f"{GREEN}============ RECEIVER: Erro ao processar chunk: {e}{RESET}")
                    continue
            
        print(f"{GREEN}============ RECEIVER: Arquivo {filename} recebido com sucesso e salvo em {destination}{RESET}")
    
    receiver.close()

def main():
    """Executa o receptor e emissor em threads separadas"""
    
    # Reseta o arquivo de log no início
    with open(LOG_FILE, "w") as log_file:
        log_file.write("Wireshark-style logs:\n")
    
    # Cria uma instância da rede compartilhada
    network = Network()
    
    # Shared running flag
    running_flag = threading.Event()
    running_flag.set()  # Set the flag to indicate threads should run
    
    try:
        # Receiver thread
        recv_thread = threading.Thread(target=receiver_thread, args=(network, running_flag), daemon=True)
        recv_thread.start()

        time.sleep(1)

        # Sender thread
        send_thread = threading.Thread(target=sender_thread, args=(network, running_flag), daemon=True)
        send_thread.start()

        recv_thread.join()
        send_thread.join()
    except KeyboardInterrupt:
        print("\nInterrupção detectada. Encerrando o programa...")
        running_flag.clear()  # Clear the flag to stop threads
    finally:
        # Fecha os sockets da rede após conclusão
        network.close()
    
if __name__ == "__main__":
    main()
