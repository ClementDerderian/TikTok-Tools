import sys
import os
import random
import requests
from ddgs import DDGS


def chercher_image(mot_cle, dossier="images"):
    os.makedirs(dossier, exist_ok=True)

    resultats = DDGS().images(
        query=mot_cle,
        max_results=30,
        safesearch="moderate"
    )

    if not resultats:
        raise Exception("Aucune image trouvée.")

    # Mélange les résultats pour avoir une image différente
    random.shuffle(resultats)

    for resultat in resultats:
        url = resultat.get("image")

        if not url:
            continue

        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10
            )

            response.raise_for_status()

            # Nom aléatoire
            nom = f"image_{random.randint(100000, 999999)}.jpg"
            chemin = os.path.join(dossier, nom)

            with open(chemin, "wb") as fichier:
                fichier.write(response.content)

            return chemin

        except Exception:
            continue

    raise Exception("Impossible de télécharger une image.")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print('Utilisation : python image.py "mot clé"')
        sys.exit(1)

    mot_cle = " ".join(sys.argv[1:])

    try:
        chemin = chercher_image(mot_cle)
        print(chemin)

    except Exception as e:
        print(f"Erreur : {e}")
        sys.exit(1)
