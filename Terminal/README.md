# Chrome Automation Terminal

Terminal personnalisé en Python permettant de gérer plusieurs sessions Google Chrome et d'automatiser certaines actions avec Selenium, notamment sur Google Flow.

## Fonctionnalités

- **Gestion de sessions Chrome**
  - `cinit` : crée et initialise une nouvelle session Chrome.
  - `copen` : ouvre une session Chrome existante.
  - Chaque session possède son propre profil et son port de débogage.
- **Automatisation Selenium**
  - Connexion aux sessions Chrome existantes.
  - Interaction avec les pages web.
  - Automatisation de tâches sur Google Flow.
- **Google Flow**
  - Suppression automatisée des médias d'un projet avec `delflow`.

## Prérequis

- Windows 10 ou Windows 11
- Python 3.10 ou supérieur
- Google Chrome

## Installation

Créer un environnement virtuel :

```powershell
python -m venv .venv
```

L'activer :

```powershell
.\.venv\Scripts\Activate.ps1
```

Installer les dépendances :

```powershell
pip install -r requirements.txt
```

## Lancement

Depuis le dossier du projet :

```powershell
python main.py
```

Adapte `main.py` si ton fichier de lancement porte un autre nom.

## Utilisation

### Gestion des sessions Chrome

Créer une session :

```text
cinit Clement
```

Créer une autre session indépendante :

```text
cinit TikTok
```

Ouvrir une session existante :

```text
copen Clement
```

```text
copen TikTok
```

Chaque session utilise son propre profil Chrome et son propre port de débogage.

### Google Flow

Supprimer progressivement les médias du projet Google Flow actuellement ouvert :

```text
delflow confirm
```

**Attention :** cette commande place les médias dans la corbeille Google Flow. Vérifie le projet ouvert avant de la lancer.

## Stockage des sessions

Les profils Chrome sont stockés dans :

```text
C:\ChromeSelenium\
```

Le fichier `sessions.json` conserve les informations nécessaires aux sessions, notamment leur nom, leur dossier de profil et leur port de débogage.

## Connexion Selenium à une session

Pour connecter une commande à une session déjà créée et ouverte :

```python
driver = connect_chrome("Clement")
```

Lorsqu'une commande se connecte à un Chrome déjà ouvert, évite d'appeler `driver.quit()` si tu souhaites conserver le navigateur et la session ouverts.

## Ajouter une commande

Créer une fonction qui reçoit les arguments :

```python
def cmd_example(args):
    terminal_print("Commande exécutée !")
```

Puis enregistrer la commande dans le dictionnaire utilisé par le terminal :

```python
COMMANDS["example"] = cmd_example
```

## Précautions

- Ne lance pas plusieurs instances de Chrome simultanément avec le même profil.
- Ne modifie pas les fichiers d'un profil Chrome pendant que celui-ci est utilisé.
- Vérifie le projet Google Flow avant toute suppression.
- Conserve une sauvegarde de `sessions.json`.

## Technologies

- Python
- Selenium
- Google Chrome
- Tkinter (inclus dans la bibliothèque standard de Python)
- JSON (inclus dans la bibliothèque standard de Python)

---

Projet personnel d'automatisation Chrome et Google Flow.
