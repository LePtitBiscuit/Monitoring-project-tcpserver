import os
import subprocess
import time
import getpass
import bcrypt


def create_service(path):
    script_path = os.path.abspath(__file__)  # Récupère le chemin absolu du script
    script_dir = os.path.dirname(script_path)  # Récupère son dossier

    with open(path, "w") as f:  # Définition du service
        f.write(
            f"""[Unit]
Description=Server TCP
After=network.target

[Service]
ExecStart=/usr/bin/python3 {script_dir}/tcpserver.py
Restart=always
User=root
Group=root
WorkingDirectory={script_dir}

[Install]
WantedBy=multi-user.target
""")

    # Installation de la bibliothèque psutil
    print("\033[33m[1/4]-Installation des pré-requis.\033[0m")
    requierements = "sudo apt update && sudo apt install python3-psutil -y"
    process = subprocess.Popen(requierements, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Lire la sortie en temps réel
    for line in process.stdout:
        print(line, end="")

    # Attendre la fin du processus et lire les erreurs si il y en a
    process.wait()
    if process.returncode != 0:
        print("Erreur rencontrée :", process.stderr.read())
    else:
        print("\033[33m[2/4]-Génération du certificat.\033[0m")
        print(
            "\033[33mLe certificat suivant vous sera demandez lors de l'enregistrement du serveur sur Tasker.\nVous pourrez toujours le retrouver en executant 'cat server-cert.pem'\n\033[0m")
        time.sleep(3)

        # Génération de la clé privé et publique du serveur
        commands = f"openssl req -x509 -newkey rsa:4096 -keyout {script_dir}/server-key.pem -out {script_dir}/server-cert.pem -days 365 -nodes -subj '/C=FR/ST=Martinique/L=Schoelcher/O=BUTInfo/OU=IT/CN=example.com'"
        process = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        process.wait()
        if process.returncode != 0:
            print("Erreur rencontrée :", process.stderr.read())
            return

        commands = f"cat {script_dir}/server-cert.pem"  # Affichage du certificat du serveur
        process = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in process.stdout:
            print("\033[35m" + line, end="\033[0m")

        process.wait()
        if process.returncode != 0:
            print("Erreur rencontrée :", process.stderr.read())
            return

        time.sleep(0.5)
        print("\n\033[33m[3/4]-Création du mot de passe.\033[0m")
        print(
            "Veuillez renseigner un mot passe. Il vous sera demander lors de la connexion au serveur depuis l'application Tasker.")
        while True:

            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(getpass.getpass("Mot de passe: ").encode(), salt)

            if bcrypt.checkpw(getpass.getpass("Confirmer le mot de passe: ").encode(), hashed):
                with open(f"{script_dir}/serverpswd.hash", "wb") as f:
                    f.write(hashed)

                break
            else:
                print("\033[31mLes mots de passe ne correspondent pas\033[0m")

        print("\033[33m[4/4]-Lancement du service.\033[0m")
        commands = "sudo systemctl daemon-reload && sudo systemctl enable remote_monitoring.service && sudo systemctl start remote_monitoring.service && sudo systemctl restart remote_monitoring.service"
        process = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Attendre la fin du processus et lire les erreurs si il y en a
        process.wait()
        if process.returncode != 0:
            print("Erreur rencontrée :", process.stderr.read())

        else:
            print("\033[32mInitialisation du service terminé.\033[0m")

if __name__ == "__main__":
    path = "/etc/systemd/system/remote_monitoring.service"
    create_service(path)

