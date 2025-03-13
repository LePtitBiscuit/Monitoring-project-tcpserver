import socket
import subprocess
import threading
import os
from collections import defaultdict
import showmetrics
import json
import time
import signal
import ssl
import bcrypt


def load_password(path):
    with open(path, "rb") as f:
        return f.read()


def show_metrics(socket, client_lock):
    with client_lock:  # Permet de ne pas écrire en meme temps
        metrics = showmetrics.get_process_usage()  # Récupération des métriques
        data = json.dumps(metrics)  # Conversion au format json
        socket.sendall(("metrics|" + data).encode("utf-8"))
        time.sleep(0.1)  # Délai pour donner le temps de tout envoyer
        socket.sendall("end".encode("utf-8"))


# Fonction pour exécuter une commande
def execute_command(command):
    try:
        # Vérifier si la commande est 'cd'
        if command[0] == "cd":
            # Utiliser os.chdir pour changer de répertoire dans le processus du serveur
            os.chdir(command[1])
            return f"Répertoire changé en {os.getcwd()}"

        elif command[0] == "Kill":
            os.kill(int(command[1]), signal.SIGTERM)
            return f"Fermeture du processus {command[1]}"

        elif command[0] == "sleep":
            subprocess.Popen(" ".join(command), shell=True, text=True)
            return f"Restarting..."

        else:
            # Exécution de la commande avec subprocess et récupération de la sortie
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return result.stdout  # Retourne la sortie standard

    except subprocess.CalledProcessError as e:
        return f"Erreur : {e}"
    except FileNotFoundError:
        return "Commande non trouvée"
    except Exception as e:
        return f"Erreur inconnue : {e}"


# Fonction qui gère chaque client
def handle_client(client_socket, client_address):
    server_password = load_password('serverpswd.hash')  # Chargement du mdp du serveur
    print(f"Connexion établie avec {client_address}")
    try:
        # Authentification
        client_password = client_socket.recv(1024).decode('utf-8').strip()
        if not bcrypt.checkpw(client_password.encode('utf-8'), server_password):
            client_socket.send("Mot de passe incorrect. Déconnexion...\n".encode('utf-8'))
            client_socket.close()
            return

        client_socket.send("Authentification réussie\n".encode('utf-8'))

        # Gérer les commandes après authentification
        client_lock = threading.Lock()
        while True:
            message = client_socket.recv(1024).decode('utf-8').strip()
            print(message)

            if message == "show_metrics":  # Lance un thread pour lé récupération des métriques
                show_metrics_thread = threading.Thread(target=show_metrics, args=(client_socket, client_lock,))
                show_metrics_thread.start()

            else:
                # Exécuter la commande et récupérer la sortie
                result = execute_command(message.split())
                if result == "Restarting...":
                    for connection in connecion_list:
                        connecion_list[connection].send(("cmd|" + result).encode('utf-8'))
                        connecion_list[connection].send("end".encode('utf-8'))
                else:
                    client_socket.send(("cmd|" + result).encode('utf-8'))
                    client_socket.send("end".encode('utf-8'))


    except Exception as e:
        print(f"Erreur avec le client {client_address}: {e}")
    finally:
        print(f"Fermeture de la connexion avec {client_address}")
        client_socket.close()


def limit_connection(client_ip):
    current_time = time.time()
    # Enregistrer la tentative de connexion
    attempts[client_ip].append(current_time)

    # Filtrer les tentatives qui sont trop anciennes
    attempts[client_ip] = [timestamp for timestamp in attempts[client_ip] if current_time - timestamp < 60]

    # Si le nombre de tentatives dépasse la limite, bloquer
    if len(attempts[client_ip]) > 5:
        return True
    return False


# Fonction principale pour démarrer le serveur
def run_server():
    global connecion_list, attempts
    connecion_list = {}
    attempts = defaultdict(list)
    # Création du socket serveur pour les commandes
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 55555))  # Écoute sur toutes les interfaces réseau sur le port 55555
    server_socket.listen(5)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile='server-cert.pem', keyfile='server-key.pem')
    print("Serveur en attente de connexions...")
    while True:

        # Acceptation de la connexion d'un client
        client_socket, client_address = server_socket.accept()
        try:
            ssl_client_socket = context.wrap_socket(client_socket, server_side=True)

            if not limit_connection(
                    client_address[0]):  # Vérifie si le client n'a pas dépassé le maximum de tentative de connexion

                connecion_list[client_address[0]] = ssl_client_socket

                # Lancer un thread pour gérer la connexion du client
                client_thread = threading.Thread(target=handle_client, args=(ssl_client_socket, client_address,))
                client_thread.start()
            else:
                ssl_client_socket.close()

        except Exception as e:
            print(f"Une erreur est survenue: {e}")


if __name__ == "__main__":
    run_server()
