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

    current_file = None
    current_file_size = 0
    bytes_received = 0
    file_data = b""

    while True:
        try:
            file_info = await websocket.recv()
            if file_info == "END_OF_FILES":
                print("Fin de la réception des fichiers.")
                break
            if isinstance(file_info, str):
                file_info = json.loads(file_info)
                current_file = os.path.join("TOSYNC", file_info["filename"])
                current_file_size = file_info["filesize"]
                bytes_received = 0
                file_data = b""
                print(
                    f"Réception du fichier {file_info['filename']} (taille : {current_file_size})"
                )

            chunk = await websocket.recv()
            file_data += chunk
            bytes_received += len(chunk)
            print(
                f"Chunk reçu ({len(chunk)} octets), total reçu pour le fichier : {bytes_received}/{current_file_size}"
            )

            if bytes_received >= current_file_size:
                with open(current_file, "wb") as f:
                    f.write(file_data)
                print(f"Fichier reçu et sauvegardé : {current_file}")

        except websockets.exceptions.ConnectionClosed:
            print("Connexion fermée.")
            break


async def main():
    print("Serveur démarré sur ws://217.160.99.153:8765")
    async with websockets.serve(handle_connection, "217.160.99.153", 8765):
        await asyncio.Future()  # Run forever

asyncio.run(main())
