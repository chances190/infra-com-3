import time
import random
import socket
import os
import threading
import struct
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

# Logs de pacotes individuais
LOG_FILE = "./Logs/logs.txt"

# Configurações de rede
SENDER_PORT = 5001
RECEIVER_PORT = 5000

SOCKET_TIMEOUT = 0.1

SENDER_ADDR = ('localhost', SENDER_PORT)
RECEIVER_ADDR = ('localhost', RECEIVER_PORT)

# Probabilidade de erro
LOSS_PROB = 0.2
CORRUPT_PROB = 0.2

# Simulação de latência de rede (em segundos)
MIN_DELAY = 0.02
MAX_DELAY = 0.5

# Timeout do RDT Send
RDT_TIMEOUT = 0.3

# Maximum time to wait for RDT operations in seconds
MAX_RDT_WAIT_TIME = 5.0

# Ajustar o tamanho máximo de transmissão para evitar estouro de buffer UDP
MAX_UDP_PACKET_SIZE = 1024

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
    
    log_message = f"{timestamp} {action.ljust(8)} ({src}) -> ({dst}) - {type_str.ljust(4)}{flags_str}\n"
    
    # Write the log message to the log file
    with open(LOG_FILE, "a") as log_file:
        log_file.write(log_message)

class UDTSocket:
    """Wrapper no Socket UDP para logar, simular latência, perda de pacotes e corrupção"""
    def __init__(self, local_addr=None, remote_addr=None):
        self.loss_prob = LOSS_PROB
        self.corrupt_prob = CORRUPT_PROB
        self.min_delay = MIN_DELAY
        self.max_delay = MAX_DELAY
        
        # Cria o socket UDP
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Vincula ao endereço local se fornecido, caso contrário usa uma porta aleatória
        if local_addr:
            self.socket.bind(local_addr)
        else:
            self.socket.bind(('localhost', 0))
        
        self.socket.settimeout(SOCKET_TIMEOUT)
        self.local_addr = self.socket.getsockname()
        self.remote_addr = remote_addr
        
        print(f"RDTConnection: Bound to {self.local_addr}")
    
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
    
    def send(self, packet):
        """Envia um pacote para o endereço remoto"""
        if not self.remote_addr:
            print("Não é possível enviar sem um endereço remoto.")
            return
            
        # Extrai informações para log
        pkt_type, seq, data_len = self._extract_packet_info(packet)
            
        # Simula perda de pacote
        if random.random() < self.loss_prob:
            log_action("DROPPED", pkt_type, seq, self.local_addr, self.remote_addr, data_len)
            return
            
        # Simula corrupção de pacote
        is_corrupt = random.random() < self.corrupt_prob
        if is_corrupt:
            packet = self._corrupt_packet(packet)
            
        # Simula atraso de rede
        self._simulate_delay()
            
        # Envia o pacote para o endereço remoto
        self.socket.sendto(packet, self.remote_addr)
        log_action("SENT", pkt_type, seq, self.local_addr, self.remote_addr, data_len)
    
    def receive(self):
        """Recebe um pacote com condições de rede simuladas"""
        try:
            # Usar um buffer maior do que o MAX_UDP_PACKET_SIZE para evitar overflow
            data, addr = self.socket.recvfrom(4096)
            
            # Atualiza o endereço remoto se não estiver definido (TOFU)
            if not self.remote_addr:
                self.remote_addr = addr
            
            # Simula atraso de rede
            self._simulate_delay()
            
            # Extrai informações para log
            pkt_type, seq, data_len = self._extract_packet_info(data)
            log_action("RECEIVED", pkt_type, seq, addr, self.local_addr, data_len)
            
            return data, addr
        except socket.timeout:
            raise
        except Exception as e:
            print(f"Erro ao receber dados: {e}")
            raise
    
    def close(self):
        """Fecha o socket UDP"""
        self.socket.close()
        print(f"RDTConnection: Closed {self.local_addr}")

class RDTSocket:
    """Socket RDT bidirecional. API similar ao Socket UDP"""
    def __init__(self, port=0, host='localhost'):
        # Cria uma conexão para a rede subjacente
        self.connection = UDTSocket(local_addr=(host, port))
        
        # Estado para envio
        self.send_state = WAIT_FOR_DATA
        self.send_seq = 0
        self.last_pkt = None
        self.last_send_time = 0
        self.timeout = RDT_TIMEOUT  # Use o valor aumentado
        
        # Estado para recebimento
        self.recv_state = WAIT_FOR_PKT0
        
        print(f"RDTSocket criado em {self.connection.local_addr}")
    
    def bind(self, address):
        """Vincula o socket a um endereço específico"""
        # Fecha a conexão existente e cria uma nova com o endereço especificado
        if self.connection:
            self.connection.close()
        self.connection = UDTSocket(local_addr=address)
    
    def connect(self, address):
        """Conecta a um endereço remoto"""
        self.connection.remote_addr = address
        print(f"RDTSocket: Conectado a {address}")
    
    def _make_pkt(self, seq, pkt_type, data):
        """Cria um pacote com os dados, tipo e sequência especificados"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        checksum = calculate_checksum(data)
        
        # Formato do pacote: [tipo (1 byte), seq (1 byte), checksum (1 byte), tamanho (4 bytes), dados]
        header = struct.pack('!BBBi', pkt_type, seq, checksum, len(data))
        return header + data
    
    def _make_ack(self, seq):
        """Cria um pacote ACK com o número de sequência especificado"""
        dummy_payload = b"ACK"
        checksum = calculate_checksum(dummy_payload)
        
        header = struct.pack('!BBBi', ACK_PKT, seq, checksum, len(dummy_payload))
        return header + dummy_payload
    
    def _unpack(self, packet):
        """Extrai informações de um pacote"""
        if len(packet) < 7:
            return None, None, None, None
        
        try:
            pkt_type, seq, checksum, data_len = struct.unpack('!BBBi', packet[:7])
            data = packet[7:]
            return pkt_type, seq, checksum, data
        except Exception:
            return None, None, None, None
    
    def send(self, data):
        """Envia dados e espera pelo ACK"""
        if self.send_state != WAIT_FOR_DATA:
            print(f"{BLUE}RDTSocket: ERRO - Tentativa de enviar dados enquanto em estado {self.send_state}{RESET}")
            return False

        # Cria um pacote com os dados
        packet = self._make_pkt(self.send_seq, DATA_PKT, data)
        self.last_pkt = packet
        
        # Envia através da conexão
        self.connection.send(packet)
        
        # Atualiza o timestamp de último envio
        self.last_send_time = time.time()
        start_time = time.time()
        
        # Muda o estado para aguardar ACK
        self.send_state = WAIT_FOR_ACK0 if (self.send_seq == 0) else WAIT_FOR_ACK1
        print(f"{BLUE}RDTSocket: Transição para estado {self.send_state}{RESET}")
        
        # Busy wait for ACK with timeout
        while self.send_state != WAIT_FOR_DATA:
            # Verifica timeout global
            if time.time() - start_time > MAX_RDT_WAIT_TIME:
                print(f"{BLUE}RDTSocket: Timeout após {MAX_RDT_WAIT_TIME}s de espera por ACK, desistindo{RESET}")
                self.send_state = WAIT_FOR_DATA
                self.last_pkt = None 
                return False
            
            # Try to receive an ACK
            if self._check_for_ack():
                return True
            
            # Check for timeout and retransmit if necessary
            self._check_timeout()
            
            # Small sleep to prevent CPU hogging
            time.sleep(0.01)
    
        return True
    
    def _check_for_ack(self):
        """Verifica se um ACK foi recebido"""
        try:
            data, addr = self.connection.receive()
            
            # Extrai o tipo de pacote, sequência e checksum
            pkt_type, seq, checksum, payload = self._unpack(data)
            
            # Verifica se é um ACK
            if pkt_type != ACK_PKT:
                return False
            
            # Verifica checksum
            if checksum != calculate_checksum(payload):
                print(f"{BLUE}RDTSocket: ACK corrompido recebido{RESET}")
                return False
            
            expected_seq = 0 if self.send_state == WAIT_FOR_ACK0 else 1
            
            # Se for o ACK esperado
            if seq == expected_seq:
                old_state = self.send_state
                self.send_state = WAIT_FOR_DATA
                self.send_seq = 1 - self.send_seq  # Alterna entre 0 e 1
                print(f"{BLUE}RDTSocket: ACK{seq} correto recebido, transição de {old_state} → {self.send_state}{RESET}")
                return True
            else:
                print(f"{BLUE}RDTSocket: ACK{seq} inesperado recebido (esperava {expected_seq}){RESET}")
                return False
                
        except socket.timeout:
            return False
        except Exception as e:
            print(f"{BLUE}RDTSocket: ERRO ao receber ACK: {e}{RESET}")
            return False
    
    def _check_timeout(self):
        """Verifica se houve timeout e retransmite se necessário"""
        if time.time() - self.last_send_time < self.timeout:
            return False
        
        seq_num = 0 if self.send_state == WAIT_FOR_ACK0 else 1
        print(f"{BLUE}RDTSocket: TIMEOUT detectado, retransmitindo pacote SEQ={seq_num}{RESET}")
        
        # Retransmite o pacote
        self.connection.send(self.last_pkt)
        self.last_send_time = time.time()
        return True
    
    def recv(self):
        """Recebe dados"""
        start_time = time.time()
        
        while True:
            # Check if we've exceeded maximum wait time
            if time.time() - start_time > MAX_RDT_WAIT_TIME:
                print(f"{GREEN}RDTSocket: Timeout após {MAX_RDT_WAIT_TIME}s de espera por pacote, desistindo{RESET}")
                return None
                
            try:
                packet, addr = self.connection.receive()
                
                # Atualiza o endereço remoto se não estiver definido (TOFU)
                if not self.connection.remote_addr:
                    self.connection.remote_addr = addr
                
                pkt_type, seq, checksum, data = self._unpack(packet)
                
                # Verifica se o checksum está correto
                is_corrupt = (checksum != calculate_checksum(data))
                
                # Ignora pacotes que não sejam de dados
                if not is_corrupt and pkt_type != DATA_PKT:
                    continue
                
                # Processa de acordo com o estado
                if self.recv_state == WAIT_FOR_PKT0:
                    if not is_corrupt and seq == 0:
                        # Pacote válido com seq=0, processamos e mudamos de estado
                        ack_packet = self._make_ack(0)
                        self.connection.send(ack_packet)
                        
                        old_state = self.recv_state
                        self.recv_state = WAIT_FOR_PKT1
                        print(f"{GREEN}RDTSocket: Pacote SEQ=0 recebido, enviando ACK0, transição de {old_state} → {self.recv_state}{RESET}")
                        
                        return data  # Retorna os dados diretamente como bytes
                    else:
                        # Pacote corrompido ou com seq=1 quando esperávamos seq=0
                        # Reenviamos ACK para o último pacote recebido com sucesso (seq=1)
                        ack_packet = self._make_ack(1)
                        self.connection.send(ack_packet)
                        if is_corrupt:
                            print(f"{GREEN}RDTSocket: Pacote corrompido recebido, permanece em {self.recv_state}{RESET}")
                        else:
                            print(f"{GREEN}RDTSocket: Pacote inválido recebido (seq incorreta), permanece em {self.recv_state}{RESET}")
                
                elif self.recv_state == WAIT_FOR_PKT1:
                    if not is_corrupt and seq == 1:
                        # Pacote válido com seq=1, processamos e mudamos de estado
                        ack_packet = self._make_ack(1)
                        self.connection.send(ack_packet)
                        
                        old_state = self.recv_state
                        self.recv_state = WAIT_FOR_PKT0
                        print(f"{GREEN}RDTSocket: Pacote SEQ=1 recebido, enviando ACK1, transição de {old_state} → {self.recv_state}{RESET}")
                        
                        return data  # Retorna os dados diretamente como bytes
                    else:
                        # Pacote corrompido ou com seq=0 quando esperávamos seq=1
                        # Reenviamos ACK para o último pacote recebido com sucesso (seq=0)
                        ack_packet = self._make_ack(0)
                        self.connection.send(ack_packet)
                        if is_corrupt:
                            print(f"{GREEN}RDTSocket: Pacote corrompido recebido, permanece em {self.recv_state}{RESET}")
                        else:
                            print(f"{GREEN}RDTSocket: Pacote inválido recebido (seq incorreta), permanece em {self.recv_state}{RESET}")
            
            except socket.timeout:
                continue
            except Exception as e:
                print(f"{GREEN}RDTSocket: ERRO ao receber pacote: {e}{RESET}")
                time.sleep(0.1)  # Adicionar pequena pausa para evitar loop infinito
    
    def close(self):
        """Fecha o socket"""
        if self.connection:
            print(f"RDTSocket {self.connection.local_addr} fechado")   
            self.connection.close()
            self.connection = None

def create_rdt_socket_pair(port_a, port_b):
    """Função auxiliar para criar um par de sockets RDT conectados"""
    socket_a = RDTSocket(port=port_a)
    socket_b = RDTSocket(port=port_b)
    
    # Conecta-os entre si
    socket_a.connect(('localhost', port_b))
    socket_b.connect(('localhost', port_a))
    
    return socket_a, socket_b

def sender_thread(socket_a):
    """Thread para envio de arquivos usando o socket RDT"""
    # Garante que o diretório existe
    if not os.path.exists(SOURCE_DIR):
        os.makedirs(SOURCE_DIR)
    
    # Lista todos os arquivos no diretório de origem
    files = [f for f in os.listdir(SOURCE_DIR) if os.path.isfile(os.path.join(SOURCE_DIR, f))]
    
    if not files:
        print(f"{BLUE}============ SENDER: Nenhum arquivo encontrado na pasta{RESET}")
        return
    
    print(f"{BLUE}============ SENDER: Encontrados {len(files)} arquivos para transferir{RESET}")
    
    # Transfere cada arquivo
    for filename in files:
        filepath = os.path.join(SOURCE_DIR, filename)
        
        print(f"{BLUE}============ SENDER: Iniciando transferência: '{filename}'{RESET}")
        
        # Envia o nome do arquivo de destino
        socket_a.send(filename.encode('utf-8'))
        
        # Envia o arquivo
        with open(filepath, 'rb') as f:
            while True:
                # Lê em chunks de 1KB
                chunk = f.read(MAX_UDP_PACKET_SIZE // 2)  # Usa um tamanho menor que o MAX_UDP_PACKET_SIZE
                if not chunk:
                    break
                    
                # Envia o chunk do arquivo
                socket_a.send(chunk)
            
        # Envia marcador de fim de arquivo
        socket_a.send(END_OF_FILE_MARKER.encode('utf-8'))
        
        print(f"{BLUE}============ SENDER: '{filename}' enviado com sucesso{RESET}")
    
    # Envia marcador de fim de transmissão
    socket_a.send(END_OF_TRANSMISSION_MARKER.encode('utf-8'))
    
    print(f"{BLUE}============ SENDER: Todos os {len(files)} arquivos foram enviados com sucesso{RESET}")

def receiver_thread(socket_b):
    """Thread para recebimento de arquivos usando o socket RDT"""
    # Garante que o diretório existe
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
    
    print(f"{GREEN}============ RECEIVER: Esperando por arquivos...{RESET}")
    
    # Recebe cada arquivo
    while True:
        # Recebe o nome do arquivo
        filename = socket_b.recv()
        
        if filename is None:
            print(f"{GREEN}============ RECEIVER: Timeout ou erro ao esperar por arquivos{RESET}")
            break
        
        # Verifica se é o sinal de fim de transmissão
        if filename == END_OF_TRANSMISSION_MARKER.encode('utf-8'):
            print(f"{GREEN}============ RECEIVER: Recebido sinal de fim de transmissão. Transferência completa.{RESET}")
            break
        
        filename = filename.decode('utf-8')
        print(f"{GREEN}============ RECEIVER: Recebendo arquivo com nome: {filename}{RESET}")

        # Renomeia o arquivo no destino para <nome>_received
        filename_appended = os.path.splitext(filename)[0] + "_received" + os.path.splitext(filename)[1]
        destination = os.path.join(DEST_DIR, filename_appended)
        
        # Garante que o diretório de destino existe
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        with open(destination, 'wb') as f:
            while True:
                # Recebe um chunk de dados
                data = socket_b.recv()
                
                if data is None:
                    print(f"{GREEN}============ RECEIVER: Erro ao receber dados{RESET}")
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

def main():
    """Executa o receptor e emissor em threads separadas, transferindo arquivos entre pastas"""
    
    # Certifica-se de que o diretório de logs existe
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    with open(LOG_FILE, "w") as log_file:
        log_file.write("Logs estilo Wireshark:\n")
    
    try:
        # Cria o par de sockets RDT conectados
        socket_a, socket_b = create_rdt_socket_pair(SENDER_PORT, RECEIVER_PORT)
        print("Sockets RDT criados e conectados entre si.")
        
        # Inicia a thread do receptor
        recv_thread = threading.Thread(target=receiver_thread, args=(socket_b,), daemon=True)
        recv_thread.start()
        print("Thread do receptor iniciada.")
        
        # Pequeno delay para garantir que o receptor está pronto
        time.sleep(1)
        
        # Inicia a thread do emissor
        send_thread = threading.Thread(target=sender_thread, args=(socket_a,), daemon=True)
        send_thread.start()
        print("Thread do emissor iniciada.")
        
        # Aguarda as threads terminarem
        recv_thread.join()
        send_thread.join()
        
        print("Transferência de arquivos concluída.")
        
    except KeyboardInterrupt:
        print("\nInterrupção detectada. Encerrando o programa...")
    finally:
        # Limpeza
        if 'socket_a' in locals():
            socket_a.close()
        if 'socket_b' in locals():
            socket_b.close()
        print("Sockets fechados.")

if __name__ == "__main__":
    main()
