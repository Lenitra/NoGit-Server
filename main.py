import asyncio
import websockets
import os
import json

# Chemin du dossier à synchroniser
SYNC_FOLDER = "/root/MultiTiles"

async def handle_connection(websocket, path):
    print(f"Nouvelle connexion : {path}")
    command = await websocket.recv()
    print(f"Commande reçue : {command}")
    
    if command == "SEND_FILES":
        await receive_files(websocket)
    elif command == "RECEIVE_FILES":
        await send_files(websocket)
    else:
        await websocket.send("Commande non reconnue.")
        await websocket.close()

async def send_files(websocket):
    print("Début de l'envoi des fichiers...")
    
    def get_file_structure(base_path):
        file_structure = {}
        for root, dirs, files in os.walk(base_path):
            rel_root = os.path.relpath(root, base_path)
            if rel_root == ".":
                rel_root = ""
            file_structure[rel_root] = files
        return file_structure

    file_structure = get_file_structure(SYNC_FOLDER)
    print(f"Structure des fichiers à envoyer : {file_structure}")
    
    # Envoyer la structure des fichiers
    await websocket.send(json.dumps(file_structure))

    # Envoyer les fichiers
    for dirpath, filenames in file_structure.items():
        for filename in filenames:
            file_path = os.path.join(SYNC_FOLDER, dirpath, filename)
            print(f"Envoi du fichier : {file_path}")
            with open(file_path, "rb") as file:
                file_data = file.read()
                # Envoyer le nom du fichier et sa taille
                await websocket.send(json.dumps({"filename": os.path.join(dirpath, filename), "filesize": len(file_data)}))
                # Envoyer les données du fichier
                await websocket.send(file_data)
    
    # Indiquer la fin de la transmission
    await websocket.send("END_OF_FILES")
    print("Envoi terminé.")

async def receive_files(websocket):
    print("Début de la réception des fichiers...")
    
    file_structure = await websocket.recv()
    print(f"Structure des fichiers reçue : {file_structure}")
    
    file_structure = json.loads(file_structure)

    # Créer les dossiers nécessaires dans le répertoire TOSYNC
    for folder in file_structure:
        os.makedirs(os.path.join("TOSYNC", folder), exist_ok=True)
    
    while True:
        try:
            # Recevoir les informations du fichier
            file_info = await websocket.recv()
            print(f"Informations du fichier reçues : {file_info}")
            if file_info == "END_OF_FILES":
                print("Fin de la réception des fichiers.")
                break
            file_info = json.loads(file_info)
            
            # Recevoir les données du fichier
            file_data = await websocket.recv()
            print(f"Réception des données pour le fichier : {file_info['filename']}")

            #remove the last split("/") to get the folder path
            file_path = SYNC_FOLDER.split("/")[:-1]
            file_path = "/".join(file_path)
            file_path = os.path.join(file_path, file_info["filename"])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Assurez-vous que le répertoire existe
            with open(file_path, "wb") as file:
                file.write(file_data)

            print(f"Fichier reçu et sauvegardé : {file_info['filename']}")
        except websockets.exceptions.ConnectionClosed:
            print("Connexion fermée.")
            break

async def main():
    print("Serveur démarré sur ws://217.160.99.153:8765")
    async with websockets.serve(handle_connection, "217.160.99.153", 8765):
        await asyncio.Future()  # Run forever

asyncio.run(main())
