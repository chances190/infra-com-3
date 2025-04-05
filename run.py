import subprocess
import sys
import time

SERVER = "Server.server"
CLIENT = "Client.repl"

if __name__ == "__main__":
    try:
        print("Iniciando Servidor...")
        subprocess.Popen(["start", "cmd", "/k", sys.executable, "-m", SERVER], shell=True)
        time.sleep(2)

        for i in range(1, 4):
            print(f"Iniciando Cliente {i}...")
            subprocess.Popen(["start", "cmd", "/k", sys.executable, "-m", CLIENT], shell=True)
            time.sleep(1)

        print("Todos os processos foram iniciados em novas janelas.")

    except KeyboardInterrupt:
        print("\nEncerrando o runner...")

    finally:
        print("Runner finalizado.")