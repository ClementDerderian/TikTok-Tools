
import tkinter as tk
from tkinter import filedialog
import os
import shutil
import platform
import json
import subprocess
import shlex
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

WINDOW_TITLE = "Clem Terminal"

BG_COLOR = "#0b0b0f"
TEXT_COLOR = "#ffffff"
PROMPT_COLOR = "#00ff88"
INPUT_COLOR = "#15151c"

FONT = ("Consolas", 11)


# ============================================================
# AFFICHAGE DANS LE TERMINAL
# ============================================================

def terminal_print(text="", color=None):

    terminal.insert(tk.END, text + "\n")

    if color:
        tag_name = f"color_{color.replace('#', '')}"

        terminal.tag_config(
            tag_name,
            foreground=color
        )

        start = terminal.index("end-2l")
        end = terminal.index("end-1l")

        terminal.tag_add(
            tag_name,
            start,
            end
        )

    terminal.see(tk.END)


# ============================================================
# COMMANDES CLASSIQUES
# ============================================================

def cmd_ls(args):

    path = args[0] if args else "."

    try:

        items = os.listdir(path)

        if not items:
            terminal_print("(dossier vide)")
            return

        for item in items:

            full_path = os.path.join(path, item)

            if os.path.isdir(full_path):

                terminal_print(
                    f"[DIR]  {item}",
                    "#55aaff"
                )

            else:

                terminal_print(
                    f"       {item}"
                )

    except FileNotFoundError:

        terminal_print(
            "Erreur : dossier introuvable.",
            "#ff5555"
        )

    except PermissionError:

        terminal_print(
            "Erreur : permission refusée.",
            "#ff5555"
        )

    except Exception as e:

        terminal_print(
            f"Erreur : {e}",
            "#ff5555"
        )


def cmd_pwd(args):

    terminal_print(
        os.getcwd(),
        PROMPT_COLOR
    )


def cmd_cd(args):

    if not args:

        terminal_print(
            "Usage : cd <dossier>",
            "#ffaa00"
        )

        return

    try:

        path = " ".join(args)

        os.chdir(path)

        terminal_print(
            f"Dossier actuel : {os.getcwd()}",
            PROMPT_COLOR
        )

    except FileNotFoundError:

        terminal_print(
            "Erreur : dossier introuvable.",
            "#ff5555"
        )

    except NotADirectoryError:

        terminal_print(
            "Erreur : ce n'est pas un dossier.",
            "#ff5555"
        )

    except PermissionError:

        terminal_print(
            "Erreur : permission refusée.",
            "#ff5555"
        )

    except Exception as e:

        terminal_print(
            f"Erreur : {e}",
            "#ff5555"
        )


def cmd_mkdir(args):

    if not args:

        terminal_print(
            "Usage : mkdir <nom>",
            "#ffaa00"
        )

        return

    for name in args:

        try:

            os.mkdir(name)

            terminal_print(
                f"Dossier créé : {name}",
                "#55ff55"
            )

        except FileExistsError:

            terminal_print(
                f"Le dossier existe déjà : {name}",
                "#ffaa00"
            )

        except Exception as e:

            terminal_print(
                f"Erreur : {e}",
                "#ff5555"
            )


def cmd_touch(args):

    if not args:

        terminal_print(
            "Usage : touch <fichier>",
            "#ffaa00"
        )

        return

    for filename in args:

        try:

            Path(filename).touch()

            terminal_print(
                f"Fichier créé : {filename}",
                "#55ff55"
            )

        except Exception as e:

            terminal_print(
                f"Erreur : {e}",
                "#ff5555"
            )


def cmd_rm(args):

    if not args:

        terminal_print(
            "Usage : rm <fichier/dossier>",
            "#ffaa00"
        )

        return

    for target in args:

        try:

            if os.path.isdir(target):

                shutil.rmtree(target)

            else:

                os.remove(target)

            terminal_print(
                f"Supprimé : {target}",
                "#55ff55"
            )

        except FileNotFoundError:

            terminal_print(
                f"Introuvable : {target}",
                "#ff5555"
            )

        except Exception as e:

            terminal_print(
                f"Erreur : {e}",
                "#ff5555"
            )


def cmd_cat(args):

    if not args:

        terminal_print(
            "Usage : cat <fichier>",
            "#ffaa00"
        )

        return

    try:

        with open(
            args[0],
            "r",
            encoding="utf-8"
        ) as file:

            terminal_print(
                file.read()
            )

    except FileNotFoundError:

        terminal_print(
            "Erreur : fichier introuvable.",
            "#ff5555"
        )

    except UnicodeDecodeError:

        terminal_print(
            "Erreur : fichier non lisible comme texte.",
            "#ff5555"
        )

    except Exception as e:

        terminal_print(
            f"Erreur : {e}",
            "#ff5555"
        )


def cmd_clear(args):

    terminal.delete(
        "1.0",
        tk.END
    )


def cmd_echo(args):

    terminal_print(
        " ".join(args)
    )


def cmd_cls(args):

    cmd_clear(args)


# ============================================================
# COMMANDES PERSONNALISÉES
# ============================================================

def cmd_hello(args):

    terminal_print(
        "Bonjour depuis ton terminal !",
        "#00ff88"
    )


def cmd_about(args):

    terminal_print("")
    terminal_print(
        "CLEM TERMINAL",
        "#00ff88"
    )
    terminal_print(
        "Terminal Python + Tkinter"
    )
    terminal_print(
        "Version 1.0"
    )
    terminal_print("")


def cmd_info(args):

    terminal_print("")
    terminal_print(
        "===== INFORMATIONS =====",
        "#00ff88"
    )
    terminal_print(
        f"Système : {platform.system()}"
    )
    terminal_print(
        f"Version : {platform.version()}"
    )
    terminal_print(
        f"Python  : {platform.python_version()}"
    )
    terminal_print(
        f"Dossier : {os.getcwd()}"
    )
    terminal_print("")


# ============================================================
# COMMANDE TIKTOK
# ============================================================


import os
import re
import json
import socket
import subprocess
import threading
import time

from pathlib import Path


CHROME_BASE = Path(r"C:\ChromeSelenium")
CHROME_CONFIG = CHROME_BASE / "sessions.json"


def load_chrome_sessions():
    CHROME_BASE.mkdir(parents=True, exist_ok=True)

    if CHROME_CONFIG.exists():
        try:
            return json.loads(
                CHROME_CONFIG.read_text(encoding="utf-8")
            )
        except Exception:
            return {}

    return {}


def save_chrome_sessions(sessions):
    CHROME_CONFIG.write_text(
        json.dumps(sessions, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )


def find_chrome():
    candidates = [
        os.path.expandvars(
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
        ),
        os.path.expandvars(
            r"%LocalAppData%\Google\Chrome\Application\chrome.exe"
        )
    ]

    for path in candidates:
        if os.path.isfile(path):
            return path

    return None


def port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def chrome_session_running(port):
    try:
        import urllib.request

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/json/version",
            timeout=1
        ) as response:
            return response.status == 200

    except Exception:
        return False


def launch_chrome_session(profile):
    sessions = load_chrome_sessions()

    if profile not in sessions:
        terminal_print(f"Profil inconnu : {profile}")
        terminal_print("Utilise cinit pour créer un profil.")
        return

    data = sessions[profile]
    port = data["port"]
    user_data = data["path"]

    if chrome_session_running(port):
        terminal_print(
            f"La session {profile} est déjà ouverte (port {port})."
        )
        return

    chrome = find_chrome()

    if not chrome:
        terminal_print("Google Chrome introuvable.")
        return

    os.makedirs(user_data, exist_ok=True)

    command = [
        chrome,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data}",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank"
    ]

    subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    for _ in range(30):
        if chrome_session_running(port):
            terminal_print(
                f"Session {profile} ouverte sur le port {port}.",
                color="green"
            )
            return

        time.sleep(0.5)

    terminal_print(
        f"Chrome lancé, mais le port {port} ne répond pas."
    )


def cmd_cinit(args):
    def worker():
        try:
            if not args:
                terminal_print("Utilisation : cinit <nom_profil>")
                return

            profile = args[0].strip()

            if not re.fullmatch(r"[A-Za-z0-9_-]+", profile):
                terminal_print(
                    "Nom invalide : utilise lettres, chiffres, _ ou -."
                )
                return

            sessions = load_chrome_sessions()

            if profile in sessions:
                terminal_print(
                    f"Le profil {profile} existe déjà."
                )
                return

            port = get_free_port()
            profile_path = CHROME_BASE / profile

            sessions[profile] = {
                "port": port,
                "path": str(profile_path)
            }

            save_chrome_sessions(sessions)

            terminal_print(f"Création du profil : {profile}")
            terminal_print(f"Port Selenium : {port}")

            launch_chrome_session(profile)

        except Exception as e:
            terminal_print(
                f"Erreur cinit : {type(e).__name__}: {e}"
            )

    threading.Thread(target=worker, daemon=True).start()


def cmd_copen(args):
    def worker():
        try:
            if not args:
                terminal_print("Utilisation : copen <nom_profil>")
                return

            profile = args[0].strip()
            sessions = load_chrome_sessions()

            if profile not in sessions:
                terminal_print(f"Profil inconnu : {profile}")
                terminal_print("Utilise cinit pour le créer.")
                return

            launch_chrome_session(profile)

        except Exception as e:
            terminal_print(
                f"Erreur copen : {type(e).__name__}: {e}"
            )

    threading.Thread(target=worker, daemon=True).start()


def cmd_tik(args):
    import os
    import subprocess
    import time
    import threading

    CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    USER_DATA = r"C:\ChromeSelenium"
    PORT = 9222
    URL = "https://www.tiktok.com/tiktokstudio/upload?from=creator_center&tab=video"

    # Utilisation :
    # tik "Profil" "C:\Videos\video.mp4" "Description" "#tag1" "#tag2" ...

    if len(args) < 3 or len(args) > 8:
        terminal_print(
            'Utilisation : tik "Profil" "Chemin vidéo" "Description" "#tag1" "#tag2" ... "#tag5"',
            "#ffaa00"
        )
        return

    profile_name = args[0]
    video_path = args[1]
    description_text = args[2]
    hashtags = args[3:]

    if not os.path.isfile(video_path):
        terminal_print(
            f"❌ Fichier introuvable : {video_path}",
            "#ff4444"
        )
        return

    # Normaliser les hashtags
    hashtags = [
        tag if tag.startswith("#") else f"#{tag}"
        for tag in hashtags
    ]

    # Construire le texte complet
    full_description = description_text
    if hashtags:
        full_description += "\n\n" + " ".join(hashtags)

    def worker():
        try:
            import pyautogui
            import pyperclip

            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.action_chains import ActionChains

            # Lancement de Chrome
            terminal_print(
                f"Lancement de Chrome : {profile_name}",
                "#00aaff"
            )

            os.makedirs(USER_DATA, exist_ok=True)

            subprocess.Popen([
                CHROME,
                f"--remote-debugging-port={PORT}",
                f"--user-data-dir={USER_DATA}",
                f"--profile-directory={profile_name}",
                URL
            ])

            time.sleep(3)

            # Connexion Selenium
            options = Options()
            options.add_experimental_option(
                "debuggerAddress",
                f"127.0.0.1:{PORT}"
            )

            driver = webdriver.Chrome(options=options)
            wait = WebDriverWait(driver, 40)

            terminal_print(
                "✅ Selenium connecté !",
                "#00ff88"
            )

            driver.get(URL)

            # Bouton de sélection de vidéo
            terminal_print(
                "Recherche du bouton vidéo...",
                "#00aaff"
            )

            bouton = wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "button.upload-stage-btn.Button__root.Button__root--shape-default.Button__root--size-large.Button__root--type-primary"
                ))
            )

            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                bouton
            )

            time.sleep(1)

            ActionChains(driver) \
                .move_to_element(bouton) \
                .pause(0.5) \
                .click() \
                .perform()

            terminal_print(
                "✅ Bouton cliqué !",
                "#00ff88"
            )

            # Sélection du fichier Windows
            time.sleep(2)

            terminal_print(
                "Sélection de la vidéo...",
                "#00aaff"
            )

            pyperclip.copy(os.path.normpath(video_path))
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.5)
            pyautogui.press("enter")

            terminal_print(
                "✅ Chemin de la vidéo envoyé.",
                "#00ff88"
            )

            # Attente du chargement
            terminal_print(
                "Attente du chargement de la vidéo...",
                "#00aaff"
            )

            time.sleep(5)

            # Trouver le champ de description
            terminal_print(
                "Recherche du champ de description...",
                "#00aaff"
            )

            description = wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    '[contenteditable="true"]'
                ))
            )

            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                description
            )

            time.sleep(1)

            # Cliquer dans le champ
            ActionChains(driver) \
                .move_to_element(description) \
                .pause(0.3) \
                .click() \
                .perform()

            time.sleep(0.5)

            # Sélectionner le contenu existant
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.3)

            # Coller la description et les hashtags
            pyperclip.copy(full_description)
            pyautogui.hotkey("ctrl", "v")

            time.sleep(0.5)

            terminal_print(
                "✅ Description et hashtags saisis !",
                "#00ff88"
            )

            terminal_print(
                f"Description : {description_text}",
                "#cccccc"
            )

            if hashtags:
                terminal_print(
                    "Hashtags : " + " ".join(hashtags),
                    "#cccccc"
                )

            terminal_print(
                "📝 Vérifie la description dans TikTok avant publication.",
                "#00aaff"
            )

        except Exception as e:
            terminal_print(
                f"❌ Erreur TikTok : {e}",
                "#ff4444"
            )

    threading.Thread(
        target=worker,
        daemon=True
    ).start()


def cmd_cresce(args):
    import os
    import subprocess
    import time
    import urllib.request
    import json

    chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    user_data = r"C:\ChromeSelenium"
    url = "https://flow.google.com/project/ce29a6b2-be48-4d19-9652-085de12eaa35"
    port_url = "http://127.0.0.1:9222/json/version"

    if len(args) != 1:
        terminal_print('Usage : cresce "Clement"', "#ffaa00")
        return

    if not os.path.isfile(chrome):
        terminal_print("Chrome introuvable : " + chrome, "#ff5555")
        return

    # Vérifie si Chrome écoute déjà sur le port.
    try:
        with urllib.request.urlopen(port_url, timeout=2) as response:
            info = json.loads(response.read().decode("utf-8"))
        terminal_print("Chrome est déjà pilotable.", "#00ff88")
        terminal_print(str(info.get("Browser", "Version inconnue")), "#55aaff")
        return
    except Exception:
        pass

    os.makedirs(user_data, exist_ok=True)

    command = [
        chrome,
        f"--user-data-dir={user_data}",
        "--profile-directory=Default",
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        url
    ]

    try:
        subprocess.Popen(command)
        terminal_print("Chrome lancé. Vérification du port...", "#55aaff")

        for _ in range(15):
            time.sleep(1)
            try:
                with urllib.request.urlopen(port_url, timeout=2) as response:
                    info = json.loads(response.read().decode("utf-8"))

                terminal_print("Connexion Chrome OK.", "#00ff88")
                terminal_print(
                    str(info.get("Browser", "Version inconnue")),
                    "#55aaff"
                )
                terminal_print("URL : " + url, "#55aaff")
                return
            except Exception:
                continue

        terminal_print(
            "ECHEC : Chrome ne répond pas sur le port 9222.",
            "#ff5555"
        )
        terminal_print(
            "Ferme tous les processus Chrome puis relance cresce.",
            "#ffaa00"
        )

    except Exception as exc:
        terminal_print(
            f"Erreur Chrome : {type(exc).__name__}: {exc}",
            "#ff5555"
        )





def cmd_gen_image(args):
    import re
    import time
    import threading
    from pathlib import Path

    def log(message, color=None):
        try:
            root.after(0, lambda m=message, c=color: terminal_print(m, c))
        except Exception:
            print(message)

    if len(args) < 2:
        log('Usage : gen_image "Clement" "C:\\Tiktok\\prompts.txt"', "#ff5555")
        return

    profile_name = args[0].strip('"')
    prompts_file = Path(args[1].strip('"'))

    if not prompts_file.is_file():
        log(f"Fichier introuvable : {prompts_file}", "#ff5555")
        return

    try:
        content = prompts_file.read_text(encoding="utf-8-sig")
        prompts = [
            p.strip()
            for p in re.findall(r"\{(.*?)\}", content, re.DOTALL)
            if p.strip()
        ]
    except Exception as exc:
        log(f"Erreur lecture fichier : {exc}", "#ff5555")
        return

    if not prompts:
        log("Aucun prompt trouvé. Format attendu : {Mon prompt}", "#ff5555")
        return

    log(f"{len(prompts)} prompts chargés.", "#55aaff")

    def worker():
        driver = None

        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            log(f"Vérification du profil Chrome : {profile_name}", "#55aaff")

            try:
                cmd_cresce([profile_name])
            except Exception as exc:
                log(f"Erreur lancement Chrome : {exc}", "#ff5555")
                return

            options = webdriver.ChromeOptions()
            options.add_experimental_option(
                "debuggerAddress", "127.0.0.1:9222"
            )

            last_error = None

            for attempt in range(15):
                try:
                    driver = webdriver.Chrome(options=options)
                    break
                except Exception as exc:
                    last_error = exc
                    log(f"Attente de Chrome... ({attempt + 1}/15)", "#ffaa00")
                    time.sleep(2)

            if driver is None:
                log(f"Connexion Selenium impossible : {last_error}", "#ff5555")
                return

            log("Selenium connecté !", "#55ff55")

            flow_tab = None

            for handle in driver.window_handles:
                try:
                    driver.switch_to.window(handle)
                    if "flow.google.com" in driver.current_url:
                        flow_tab = handle
                        break
                except Exception:
                    continue

            if flow_tab is None:
                log("Aucun onglet Google Flow trouvé.", "#ff5555")
                return

            driver.switch_to.window(flow_tab)
            wait = WebDriverWait(driver, 20)

            log("Configuration du mode image...", "#55aaff")

            # Le bouton de réglages affiche le modèle, le format et le nombre.
            settings = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.settings-trigger-button")
                )
            )

            summary = settings.text.lower()

            # Vérification du modèle image.
            if "nano banana" not in summary:
                log(
                    f"Le modèle actuel n'est pas Nano Banana : {settings.text}",
                    "#ff5555"
                )
                log(
                    "Arrêt par sécurité : sélectionne un modèle image dans Flow.",
                    "#ffaa00"
                )
                return

            log("Modèle image Nano Banana détecté.", "#55ff55")

            # Ouvrir les paramètres.
            settings.click()
            time.sleep(1)

            # Récupérer les options visibles du panneau de réglages.
            def click_visible_option(pattern):
                return driver.execute_script("""
                    const pattern = new RegExp(arguments[0], 'i');

                    const elements = Array.from(document.querySelectorAll(
                        'button, [role="radio"], [role="option"], ' +
                        '[role="menuitem"], mat-button-toggle, ' +
                        '.mat-mdc-menu-item'
                    ));

                    const candidates = elements.filter(el => {
                        const rect = el.getBoundingClientRect();
                        const text = (el.innerText || el.getAttribute('aria-label') || '').trim();

                        return rect.width > 0 &&
                               rect.height > 0 &&
                               pattern.test(text);
                    });

                    if (!candidates.length) return null;

                    const el = candidates[candidates.length - 1];
                    el.click();

                    return (el.innerText || el.getAttribute('aria-label') || '').trim();
                """, pattern)

            # Vérifier le format vertical 9:16.
            summary = driver.find_element(
                By.CSS_SELECTOR, "button.settings-trigger-button"
            ).text.lower()

            if "crop_9_16" not in summary and "9:16" not in summary:
                log("Sélection du format vertical 9:16...", "#ffaa00")

                selected_ratio = click_visible_option(
                    r"^(9\s*:\s*16|portrait|vertical)$"
                )

                if not selected_ratio:
                    log(
                        "Option 9:16 introuvable dans les réglages. "
                        "Je préfère arrêter plutôt que choisir un mauvais format.",
                        "#ff5555"
                    )
                    return

                time.sleep(0.7)

            else:
                log("Format TikTok 9:16 déjà sélectionné.", "#55ff55")

            # Sélectionner exactement 3 images.
            summary = driver.find_element(
                By.CSS_SELECTOR, "button.settings-trigger-button"
            ).text.lower()

            if not re.search(r"\bx3\b", summary):
                log("Sélection de 3 images...", "#ffaa00")

                selected_count = click_visible_option(
                    r"^(3|x3|3 images|3 images par prompt)$"
                )

                if not selected_count:
                    # Afficher les options visibles pour faciliter le prochain ajustement.
                    visible_options = driver.execute_script("""
                        return Array.from(document.querySelectorAll(
                            'button, [role="radio"], [role="option"], ' +
                            '[role="menuitem"], mat-button-toggle'
                        )).filter(el => {
                            const r = el.getBoundingClientRect();
                            return r.width > 0 && r.height > 0;
                        }).map(el =>
                            (el.innerText || el.getAttribute('aria-label') || '').trim()
                        ).filter(Boolean);
                    """)

                    log("Options visibles : " + " | ".join(visible_options[:30]), "#ffaa00")
                    log(
                        "Impossible de trouver l'option 3 images. "
                        "Aucun prompt n'a été envoyé.",
                        "#ff5555"
                    )
                    return

                time.sleep(0.7)

            # Vérification finale des paramètres.
            settings = driver.find_element(
                By.CSS_SELECTOR, "button.settings-trigger-button"
            )
            final_summary = settings.text.lower()

            if "nano banana" not in final_summary:
                log("Le mode image n'est plus confirmé.", "#ff5555")
                return

            if "crop_9_16" not in final_summary and "9:16" not in final_summary:
                log(f"Format vertical non confirmé : {settings.text}", "#ff5555")
                return

            if not re.search(r"\bx3\b", final_summary):
                log(f"Le réglage x3 n'est pas confirmé : {settings.text}", "#ff5555")
                return

            log(f"Configuration validée : {settings.text}", "#55ff55")

            # Fermer le panneau si nécessaire.
            settings.click()
            time.sleep(0.5)

            selector = (
                "flow-rich-text-editor.prompt-input "
                "[role='textbox'][contenteditable='true']"
            )

            for index, prompt in enumerate(prompts, start=1):
                log(
                    f"[{index}/{len(prompts)}] Recherche du champ...",
                    "#ffaa00"
                )

                try:
                    editor = wait.until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, selector)
                        )
                    )

                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});",
                        editor
                    )

                    editor.click()
                    editor.send_keys(Keys.CONTROL, "a")
                    editor.send_keys(Keys.BACKSPACE)
                    editor.send_keys(prompt)

                    time.sleep(0.5)

                    current_text = (
                        editor.get_attribute("innerText")
                        or editor.text
                        or ""
                    )

                    if prompt.strip() not in current_text:
                        log("Le texte n'est pas confirmé dans le champ.", "#ff5555")
                        return

                    log(
                        f"[{index}/{len(prompts)}] Texte saisi et vérifié.",
                        "#55ff55"
                    )

                    generate_button = driver.find_element(
                        By.CSS_SELECTOR, "button.generate-icon-button"
                    )

                    if not generate_button.is_enabled():
                        log("Le bouton de génération est désactivé.", "#ff5555")
                        return

                    generate_button.click()

                    log(
                        f"[{index}/{len(prompts)}] Génération lancée : 3 images.",
                        "#55ff55"
                    )

                except Exception as exc:
                    log(
                        f"Erreur au prompt {index} : {type(exc).__name__}: {exc}",
                        "#ff5555"
                    )
                    return

                if index < len(prompts):
                    log(
                        "Attente de 60 secondes avant le prochain prompt...",
                        "#ffaa00"
                    )
                    time.sleep(60)

            log("Tous les prompts ont été traités !", "#55ff55")

        except Exception as exc:
            log(
                f"Erreur gen_image : {type(exc).__name__}: {exc}",
                "#ff5555"
            )

    threading.Thread(target=worker, daemon=True).start()





def cmd_save_img(args):
    import os
    import time
    import requests
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    folder = args[0] if args else "images"
    os.makedirs(folder, exist_ok=True)

    def worker():
        driver = None
        try:
            terminal_print("Recherche des images Google Flow...")

            options = Options()
            options.add_experimental_option(
                "debuggerAddress", "127.0.0.1:9222"
            )
            driver = webdriver.Chrome(options=options)

            if "flow.google.com" not in driver.current_url:
                terminal_print("Erreur : ouvre d'abord Google Flow.")
                return

            images = driver.execute_script("""
                const tiles = document.querySelectorAll(
                    '.tile-row.virtual-item-container flow-image-tile'
                );

                return Array.from(tiles).map(tile => {
                    const img = tile.querySelector('img.image');
                    return {
                        id: tile.getAttribute('data-media-id')
                            || img?.getAttribute('data-media-id'),
                        url: img?.currentSrc || img?.src
                    };
                }).filter(img => img.url);
            """)

            unique = {}
            for img in images:
                key = img["id"] or img["url"]
                unique[key] = img

            images = list(unique.values())
            terminal_print(f"{len(images)} image(s) trouvée(s).")

            session = requests.Session()

            for cookie in driver.get_cookies():
                session.cookies.set(
                    cookie["name"],
                    cookie["value"],
                    domain=cookie.get("domain"),
                    path=cookie.get("path", "/")
                )

            session.headers.update({
                "User-Agent": driver.execute_script(
                    "return navigator.userAgent"
                ),
                "Referer": driver.current_url
            })

            saved = 0

            for i, img in enumerate(images, 1):
                try:
                    response = session.get(
                        img["url"],
                        timeout=30
                    )
                    response.raise_for_status()

                    content_type = response.headers.get(
                        "Content-Type", ""
                    ).lower()

                    extensions = {
                        "image/png": ".png",
                        "image/jpeg": ".jpg",
                        "image/webp": ".webp",
                        "image/gif": ".gif"
                    }

                    ext = next(
                        (v for k, v in extensions.items()
                         if k in content_type),
                        ".jpg"
                    )

                    filename = img["id"] or f"image_{i}"
                    path = os.path.join(folder, filename + ext)

                    with open(path, "wb") as f:
                        f.write(response.content)

                    saved += 1
                    terminal_print(
                        f"[{i}/{len(images)}] Image sauvegardée : {filename}{ext}"
                    )

                except Exception as e:
                    terminal_print(
                        f"Erreur image {img['id']}: {e}"
                    )

            terminal_print(
                f"Terminé : {saved}/{len(images)} image(s) sauvegardée(s)."
            )
            terminal_print(f"Dossier : {os.path.abspath(folder)}")

        except Exception as e:
            terminal_print(f"Erreur save_img : {e}")

        finally:
            if driver:
                driver.quit()

    import threading
    threading.Thread(target=worker, daemon=True).start()



def cmd_delflow(args):
    import threading
    import time

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.common.exceptions import (
        NoSuchElementException,
        StaleElementReferenceException,
        TimeoutException
    )

    def worker():
        driver = None

        try:
            if not args or args[0].lower() != "confirm":
                terminal_print("ATTENTION :")
                terminal_print(
                    "Tous les médias du projet Google Flow "
                    "seront placés dans la corbeille."
                )
                terminal_print("Pour confirmer : delflow confirm")
                return

            terminal_print("Connexion à Google Flow...")

            options = Options()
            options.add_experimental_option(
                "debuggerAddress", "127.0.0.1:9222"
            )

            driver = webdriver.Chrome(options=options)

            # Trouver le projet Google Flow
            flow_tab = None

            for handle in driver.window_handles:
                driver.switch_to.window(handle)

                if "flow.google.com/project/" in driver.current_url:
                    flow_tab = handle
                    break

            if flow_tab is None:
                terminal_print("Erreur : projet Google Flow introuvable.")
                return

            driver.switch_to.window(flow_tab)

            wait = WebDriverWait(driver, 10)

            time.sleep(3)

            # Remonter en haut de la galerie
            driver.execute_script("""
                const viewport = document.querySelector(
                    'cdk-virtual-scroll-viewport'
                );

                if (viewport) {
                    viewport.scrollTop = 0;
                }
            """)

            time.sleep(2)

            def get_first_tile():
                return driver.execute_script("""
                    const elements = [
                        ...document.querySelectorAll('[data-media-id]')
                    ];

                    for (const element of elements) {
                        const tile = element.closest(
                            'flow-image-tile, flow-video-tile'
                        );

                        if (tile && tile.querySelector(
                            'button[aria-label="Autres options"]'
                        )) {
                            return {
                                id: element.getAttribute('data-media-id'),
                                type: tile.tagName.toLowerCase()
                            };
                        }
                    }

                    return null;
                """)

            def scroll_to_top():
                driver.execute_script("""
                    const viewport = document.querySelector(
                        'cdk-virtual-scroll-viewport'
                    );

                    if (viewport) {
                        viewport.scrollTop = 0;
                    }
                """)

            deleted = 0
            errors = 0
            max_errors = 5
            max_items = 1000

            terminal_print("Début du nettoyage...")

            while deleted < max_items:
                scroll_to_top()
                time.sleep(0.5)

                tile_data = get_first_tile()

                if tile_data is None:
                    terminal_print(
                        "Aucun autre média détecté en haut de la galerie."
                    )
                    break

                media_id = tile_data["id"]

                try:
                    # Récupérer la vignette à partir de son ID
                    element = driver.find_element(
                        By.CSS_SELECTOR,
                        f'[data-media-id="{media_id}"]'
                    )

                    tile = driver.execute_script("""
                        return arguments[0].closest(
                            'flow-image-tile, flow-video-tile'
                        );
                    """, element)

                    menu_button = tile.find_element(
                        By.CSS_SELECTOR,
                        'button[aria-label="Autres options"]'
                    )

                    driver.execute_script(
                        "arguments[0].click();",
                        menu_button
                    )

                    # Attendre l'ouverture du menu
                    menu = wait.until(
                        lambda d: d.find_element(
                            By.CSS_SELECTOR,
                            '[role="menu"]'
                        )
                    )

                    # Identifier l'option de suppression
                    delete_button = menu.find_element(
                        By.XPATH,
                        ".//button[@role='menuitem' and "
                        ".//mat-icon[normalize-space()='delete']]"
                    )

                    delete_button.click()

                    # Attendre que le média disparaisse
                    WebDriverWait(driver, 10).until(
                        lambda d: not d.execute_script("""
                            return [...document.querySelectorAll(
                                '[data-media-id]'
                            )].some(
                                el => el.getAttribute('data-media-id')
                                    === arguments[0]
                            );
                        """, media_id)
                    )

                    deleted += 1
                    errors = 0

                    terminal_print(
                        f"[SUPPRIMÉ] {media_id} | Total : {deleted}",
                        color="green"
                    )

                    time.sleep(0.4)

                except StaleElementReferenceException:
                    # La galerie s'est actualisée : recommencer
                    continue

                except TimeoutException:
                    terminal_print(
                        f"[ERREUR] Délai dépassé pour {media_id}"
                    )
                    errors += 1

                except NoSuchElementException:
                    terminal_print(
                        f"[ERREUR] Menu introuvable pour {media_id}"
                    )
                    errors += 1

                except Exception as e:
                    terminal_print(
                        f"[ERREUR] {media_id} : {e}"
                    )
                    errors += 1

                if errors >= max_errors:
                    terminal_print(
                        "Arrêt de sécurité : trop d'erreurs consécutives."
                    )
                    break

            terminal_print("")
            terminal_print("==============================")
            terminal_print("NETTOYAGE TERMINÉ")
            terminal_print(f"Médias placés dans la corbeille : {deleted}")
            terminal_print(f"Erreurs : {errors}")
            terminal_print("==============================")

            terminal_print(
                "Les médias restent récupérables dans la corbeille."
            )

        except Exception as e:
            terminal_print(
                f"Erreur delflow : {type(e).__name__}: {e}"
            )

        finally:
            # Ne pas fermer Chrome : session existante.
            pass

    threading.Thread(target=worker, daemon=True).start()



# ============================================================
# TABLE DES COMMANDES
# ============================================================

COMMANDS = {

    "ls": cmd_ls,
    "pwd": cmd_pwd,
    "cd": cmd_cd,
    "mkdir": cmd_mkdir,
    "touch": cmd_touch,
    "rm": cmd_rm,
    "cat": cmd_cat,

    "clear": cmd_clear,
    "cls": cmd_cls,
    "echo": cmd_echo,

    "hello": cmd_hello,
    "about": cmd_about,
    "info": cmd_info,

    "cinit": cmd_cinit,
    "copen": cmd_copen,
    "tik": cmd_tik,
    "cresce": cmd_cresce,
    "gen_image": cmd_gen_image,
    "save_img": cmd_save_img,
    "delflow": cmd_delflow,

}


# ============================================================
# HELP
# ============================================================

def cmd_help(args):

    terminal_print("")

    terminal_print(
        "===== COMMANDES DISPONIBLES =====",
        "#00ff88"
    )

    terminal_print("")

    for command in COMMANDS:

        terminal_print(
            f"  {command}"
        )

    terminal_print("")

    terminal_print(
        "exit / quit  -> fermer le terminal",
        "#ffaa00"
    )

    terminal_print("")


COMMANDS["help"] = cmd_help


# ============================================================
# EXÉCUTER UNE COMMANDE
# ============================================================

def execute_command(event=None):

    command_line = command_entry.get().strip()

    if not command_line:

        return

    terminal_print(
        f"{os.getcwd()} > {command_line}",
        PROMPT_COLOR
    )

    command_entry.delete(
        0,
        tk.END
    )

    try:

        parts = shlex.split(
            command_line
        )

    except ValueError:

        terminal_print(
            "Erreur : guillemets incorrects.",
            "#ff5555"
        )

        return

    if not parts:

        return

    command = parts[0]

    args = parts[1:]

    if command.lower() in (
        "exit",
        "quit"
    ):

        root.destroy()

        return

    if command.lower() in COMMANDS:

        try:

            COMMANDS[
                command.lower()
            ](args)

        except Exception as e:

            terminal_print(
                f"Erreur : {e}",
                "#ff5555"
            )

    else:

        terminal_print(
            f"Commande inconnue : {command}",
            "#ff5555"
        )

        terminal_print(
            "Tape 'help' pour voir les commandes.",
            "#ffaa00"
        )


# ============================================================
# CHOISIR UNE IMAGE DE FOND
# ============================================================

def choose_background():

    global background_image

    filename = filedialog.askopenfilename(

        title="Choisir une image",

        filetypes=[
            (
                "Images",
                "*.png *.jpg *.jpeg *.gif"
            ),
            (
                "Tous les fichiers",
                "*.*"
            )
        ]
    )

    if not filename:

        return

    try:

        background_image = tk.PhotoImage(
            file=filename
        )

        background_label.configure(
            image=background_image
        )

    except Exception:

        terminal_print(
            "Erreur : image non compatible.",
            "#ff5555"
        )


# ============================================================
# FENÊTRE PRINCIPALE
# ============================================================

root = tk.Tk()

root.title(
    WINDOW_TITLE
)

root.geometry(
    "1000x650"
)

root.minsize(
    700,
    450
)

root.configure(
    bg=BG_COLOR
)


# ============================================================
# IMAGE DE FOND
# ============================================================

background_image = None

background_label = tk.Label(
    root,
    bg=BG_COLOR
)

background_label.place(
    x=0,
    y=0,
    relwidth=1,
    relheight=1
)


# ============================================================
# BARRE DU HAUT
# ============================================================

top_bar = tk.Frame(
    root,
    bg="#111118",
    height=45
)

top_bar.pack(
    fill="x"
)

top_bar.pack_propagate(
    False
)


title = tk.Label(
    top_bar,
    text="  CLEM TERMINAL",
    bg="#111118",
    fg="#ffffff",
    font=(
        "Consolas",
        12,
        "bold"
    )
)

title.pack(
    side="left",
    padx=10
)


background_button = tk.Button(
    top_bar,
    text="Fond",
    command=choose_background,
    bg="#20202a",
    fg="white",
    activebackground="#30303a",
    activeforeground="white",
    relief="flat",
    padx=12
)

background_button.pack(
    side="right",
    padx=10
)


# ============================================================
# ZONE TERMINAL
# ============================================================

terminal_frame = tk.Frame(
    root,
    bg=BG_COLOR
)

terminal_frame.pack(
    fill="both",
    expand=True,
    padx=15,
    pady=(15, 5)
)


terminal = tk.Text(
    terminal_frame,

    bg=BG_COLOR,

    fg=TEXT_COLOR,

    insertbackground=TEXT_COLOR,

    font=FONT,

    relief="flat",

    borderwidth=0,

    wrap="word"
)

terminal.pack(
    fill="both",
    expand=True
)


# ============================================================
# ZONE DE SAISIE
# ============================================================

input_frame = tk.Frame(
    root,
    bg="#111118"
)

input_frame.pack(
    fill="x",
    padx=15,
    pady=15
)


prompt = tk.Label(
    input_frame,

    text=">",

    bg="#111118",

    fg=PROMPT_COLOR,

    font=(
        "Consolas",
        12,
        "bold"
    )
)

prompt.pack(
    side="left",
    padx=(10, 5)
)


command_entry = tk.Entry(

    input_frame,

    bg=INPUT_COLOR,

    fg=TEXT_COLOR,

    insertbackground=TEXT_COLOR,

    font=FONT,

    relief="flat"
)

command_entry.pack(
    side="left",

    fill="x",

    expand=True,

    ipady=8,

    padx=(0, 10)
)


command_entry.bind(
    "<Return>",
    execute_command
)


# ============================================================
# MESSAGE DE DÉMARRAGE
# ============================================================

terminal_print(
    "========================================",
    "#00ff88"
)

terminal_print(
    "          CLEM TERMINAL",
    "#00ff88"
)

terminal_print(
    "========================================",
    "#00ff88"
)

terminal_print("")

terminal_print(
    "Tape 'help' pour voir les commandes.",
    "#aaaaaa"
)

terminal_print("")

terminal_print(
    f"Dossier actuel : {os.getcwd()}",
    PROMPT_COLOR
)

terminal_print("")


# ============================================================
# FOCUS
# ============================================================

command_entry.focus_set()


# ============================================================
# LANCEMENT
# ============================================================

root.mainloop()
