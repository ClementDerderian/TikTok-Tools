import tkinter as tk
from tkinter import filedialog
import os
import io
import re
import shutil
import platform
import json
import subprocess
import shlex
import socket
import sys
import queue
import collections
import time
import threading
import base64 as _b64
import hashlib as _hashlib
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from cd_language import CDInterpreter, CDEditor, EDITOR_NAME


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

# Chaque onglet fait tourner ses commandes dans un processus « worker » : ici
# terminal_print n'écrit pas dans un widget, il envoie l'affichage à l'onglet.
# (Dans la fenêtre principale, _manager_sink affiche dans l'onglet actif.)

WORKER_MODE = "--worker" in sys.argv[1:]
_proto_out = None          # worker : flux réservé au protocole (voir worker_main)
_proto_lock = threading.Lock()
_manager_sink = None


def _emit(event):
    if _proto_out is None:
        return
    with _proto_lock:
        try:
            _proto_out.write(json.dumps(event, ensure_ascii=False) + "\n")
            _proto_out.flush()
        except (OSError, ValueError):
            pass


def terminal_print(text="", color=None):
    if WORKER_MODE:
        _emit({"e": "print", "text": text, "color": color})
    elif _manager_sink is not None:
        _manager_sink(text, color)
    else:
        print(text)


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
                terminal_print(f"[DIR]  {item}", "#55aaff")
            else:
                terminal_print(f"       {item}")
    except FileNotFoundError:
        terminal_print("Erreur : dossier introuvable.", "#ff5555")
    except PermissionError:
        terminal_print("Erreur : permission refusée.", "#ff5555")
    except Exception as e:
        terminal_print(f"Erreur : {e}", "#ff5555")


def cmd_pwd(args):
    terminal_print(os.getcwd(), PROMPT_COLOR)


def cmd_cd(args):
    if not args:
        terminal_print("Usage : cd <dossier>", "#ffaa00")
        return
    try:
        path = " ".join(args)
        os.chdir(path)
        terminal_print(f"Dossier actuel : {os.getcwd()}", PROMPT_COLOR)
    except FileNotFoundError:
        terminal_print("Erreur : dossier introuvable.", "#ff5555")
    except NotADirectoryError:
        terminal_print("Erreur : ce n'est pas un dossier.", "#ff5555")
    except PermissionError:
        terminal_print("Erreur : permission refusée.", "#ff5555")
    except Exception as e:
        terminal_print(f"Erreur : {e}", "#ff5555")


def cmd_mkdir(args):
    if not args:
        terminal_print("Usage : mkdir <nom>", "#ffaa00")
        return
    for name in args:
        try:
            os.mkdir(name)
            terminal_print(f"Dossier créé : {name}", "#55ff55")
        except FileExistsError:
            terminal_print(f"Le dossier existe déjà : {name}", "#ffaa00")
        except Exception as e:
            terminal_print(f"Erreur : {e}", "#ff5555")


def cmd_touch(args):
    if not args:
        terminal_print("Usage : touch <fichier>", "#ffaa00")
        return
    for filename in args:
        try:
            Path(filename).touch()
            terminal_print(f"Fichier créé : {filename}", "#55ff55")
        except Exception as e:
            terminal_print(f"Erreur : {e}", "#ff5555")


def cmd_rm(args):
    if not args:
        terminal_print("Usage : rm <fichier/dossier>", "#ffaa00")
        return
    for target in args:
        try:
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)
            terminal_print(f"Supprimé : {target}", "#55ff55")
        except FileNotFoundError:
            terminal_print(f"Introuvable : {target}", "#ff5555")
        except Exception as e:
            terminal_print(f"Erreur : {e}", "#ff5555")


def cmd_cat(args):
    if not args:
        terminal_print("Usage : cat <fichier>", "#ffaa00")
        return
    try:
        with open(args[0], "r", encoding="utf-8") as file:
            terminal_print(file.read())
    except FileNotFoundError:
        terminal_print("Erreur : fichier introuvable.", "#ff5555")
    except UnicodeDecodeError:
        terminal_print("Erreur : fichier non lisible comme texte.", "#ff5555")
    except Exception as e:
        terminal_print(f"Erreur : {e}", "#ff5555")


def cmd_clear(args):
    _emit({"e": "clear"})


def cmd_echo(args):
    terminal_print(" ".join(args))


def cmd_cls(args):
    cmd_clear(args)


# ============================================================
# COMMANDES PERSONNALISÉES
# ============================================================

def cmd_fivi(args):
    """fivi <fichier> <n> : affiche la ligne n du fichier, sans les { }."""
    if len(args) != 2:
        terminal_print('Usage : fivi "fichier" n   (ou : fivi n "fichier")', "#ffaa00")
        return

    # Accepte les deux ordres : le numéro est l'argument qui est un entier
    if args[1].strip().isdigit():
        file_arg, n_arg = args[0], args[1]
    elif args[0].strip().isdigit():
        file_arg, n_arg = args[1], args[0]
    else:
        terminal_print("Erreur : n doit être un nombre entier.", "#ff5555")
        return

    n = int(n_arg)
    if n < 1:
        terminal_print("Erreur : n doit être supérieur ou égal à 1.", "#ff5555")
        return

    path = Path(file_arg.strip().strip('"')).expanduser()
    if not path.is_file():
        terminal_print(f"Fichier introuvable : {path}", "#ff5555")
        return

    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except UnicodeDecodeError:
        terminal_print("Erreur : fichier non lisible comme texte.", "#ff5555")
        return
    except Exception as e:
        terminal_print(f"Erreur : {e}", "#ff5555")
        return

    if n > len(lines):
        terminal_print(f"Le fichier n'a que {len(lines)} ligne(s).", "#ffaa00")
        return

    text = lines[n - 1].replace("{", "").replace("}", "").strip()
    terminal_print(text)
    return text  # permet : b = fivi video.txt 1


def cmd_hello(args):
    terminal_print("Bonjour depuis ton terminal !", "#00ff88")


def cmd_about(args):
    terminal_print("")
    terminal_print("CLEM TERMINAL", "#00ff88")
    terminal_print("Terminal Python + Tkinter")
    terminal_print("Version 1.0")
    terminal_print("")


def cmd_info(args):
    terminal_print("")
    terminal_print("===== INFORMATIONS =====", "#00ff88")
    terminal_print(f"Système : {platform.system()}")
    terminal_print(f"Version : {platform.version()}")
    terminal_print(f"Python  : {platform.python_version()}")
    terminal_print(f"Dossier : {os.getcwd()}")
    terminal_print("")


# ============================================================
# SESSIONS CHROME
# ============================================================

CHROME_BASE = Path(r"C:\ChromeSelenium")
CHROME_CONFIG = CHROME_BASE / "sessions.json"
FLOW_HOME = "https://flow.google.com/"


def get_flow_project_url(profile):
    """Retourne l'URL Flow mémorisée pour ce profil Chrome."""
    data = load_chrome_sessions().get(profile, {})
    return data.get("flow_project_url")


def set_flow_project_url(profile, url):
    """Mémorise l'URL du projet Flow pour un profil Chrome."""
    if not url.startswith("https://flow.google.com/project/"):
        raise ValueError("L'URL doit être une URL de projet Google Flow.")
    sessions = load_chrome_sessions()
    data = sessions.get(profile) or ensure_chrome_session(profile)
    # ensure_chrome_session a pu réécrire le fichier : on relit
    sessions = load_chrome_sessions()
    data = sessions.get(profile, data)
    data["flow_project_url"] = url.split("?", 1)[0].rstrip("/")
    sessions[profile] = data
    save_chrome_sessions(sessions)
    return data["flow_project_url"]


def load_chrome_sessions():
    CHROME_BASE.mkdir(parents=True, exist_ok=True)
    if CHROME_CONFIG.exists():
        try:
            return json.loads(CHROME_CONFIG.read_text(encoding="utf-8"))
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
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
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
            f"http://127.0.0.1:{port}/json/version", timeout=1
        ) as response:
            return response.status == 200
    except Exception:
        return False


def ensure_chrome_session(profile):
    """Récupère l'ancienne session 9222 ou crée un profil isolé."""
    sessions = load_chrome_sessions()

    if profile in sessions:
        return sessions[profile]

    # Migration de l'ancienne session commune C:\ChromeSelenium / port 9222.
    if chrome_session_running(9222):
        data = {"port": 9222, "path": str(CHROME_BASE)}
        sessions[profile] = data
        save_chrome_sessions(sessions)
        terminal_print(
            f"Ancienne session Chrome récupérée pour {profile} (port 9222).",
            "#55ff55"
        )
        return data

    port = get_free_port()
    profile_path = CHROME_BASE / profile
    data = {"port": port, "path": str(profile_path)}
    sessions[profile] = data
    save_chrome_sessions(sessions)
    return data


def get_chrome_port(profile):
    data = ensure_chrome_session(profile)
    return int(data["port"])


def get_default_chrome_profile():
    sessions = load_chrome_sessions()
    if "Clement" in sessions:
        return "Clement"
    if sessions:
        return next(iter(sessions))
    if chrome_session_running(9222):
        ensure_chrome_session("Clement")
        return "Clement"
    raise RuntimeError("Aucun profil Chrome initialisé. Utilise cinit Clement.")


def launch_chrome_session(profile, url="about:blank"):
    data = ensure_chrome_session(profile)
    port = int(data["port"])
    user_data = data["path"]

    if chrome_session_running(port):
        terminal_print(
            f"La session {profile} est déjà ouverte (port {port}).",
            "#55ff55"
        )
        return True

    chrome = find_chrome()
    if not chrome:
        terminal_print("Google Chrome introuvable.", "#ff5555")
        return False

    os.makedirs(user_data, exist_ok=True)
    command = [
        chrome,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data}",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        url,
    ]

    subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for _ in range(30):
        if chrome_session_running(port):
            terminal_print(f"Session {profile} ouverte sur le port {port}.", "#55ff55")
            return True
        time.sleep(0.5)

    terminal_print(f"Chrome lancé, mais le port {port} ne répond pas.", "#ff5555")
    return False


def connect_selenium(profile, url="about:blank", log=None, retries=15):
    """Lance (si besoin) Chrome pour `profile` puis connecte Selenium.

    Le port est relu APRÈS le lancement, puis vérifié, ce qui évite
    de se connecter à un autre port que celui où Chrome a été ouvert.
    Retourne le driver, ou None en cas d'échec.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    log = log or terminal_print

    ensure_chrome_session(profile)
    if not launch_chrome_session(profile, url):
        return None

    port = int(load_chrome_sessions()[profile]["port"])
    for _ in range(20):
        if chrome_session_running(port):
            break
        time.sleep(0.5)
    else:
        log(f"Chrome ne répond pas sur le port {port}.", "#ff5555")
        return None

    log(f"Connexion Selenium sur le port {port}", "#55aaff")

    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")

    last_error = None
    for attempt in range(retries):
        try:
            return webdriver.Chrome(options=options)
        except Exception as exc:
            last_error = exc
            log(f"Attente de Chrome... ({attempt + 1}/{retries})", "#ffaa00")
            time.sleep(2)

    log(f"Connexion Selenium impossible : {last_error}", "#ff5555")
    return None


def cmd_cinit(args):
    def worker():
        try:
            if not args:
                terminal_print("Utilisation : cinit <nom_profil>")
                return

            profile = args[0].strip()
            if not re.fullmatch(r"[A-Za-z0-9_-]+", profile):
                terminal_print("Nom invalide : utilise lettres, chiffres, _ ou -.", "#ff5555")
                return

            sessions = load_chrome_sessions()
            if profile in sessions:
                data = sessions[profile]
                terminal_print(
                    f"Le profil {profile} existe déjà (port {data['port']}).",
                    "#ffaa00"
                )
                launch_chrome_session(profile)
                return

            data = ensure_chrome_session(profile)
            terminal_print(f"Création du profil : {profile}", "#55aaff")
            terminal_print(f"Port Selenium : {data['port']}", "#55aaff")
            launch_chrome_session(profile)

        except Exception as e:
            terminal_print(f"Erreur cinit : {type(e).__name__}: {e}", "#ff5555")

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
                if chrome_session_running(9222):
                    terminal_print("Récupération de l'ancienne session 9222...", "#55aaff")
                    ensure_chrome_session(profile)
                else:
                    available = ", ".join(sessions.keys()) or "aucun"
                    terminal_print(f"Profil inconnu : {profile}", "#ff5555")
                    terminal_print(f"Profils enregistrés : {available}", "#ffaa00")
                    terminal_print("Utilise exactement le nom créé avec cinit.", "#ffaa00")
                    return

            launch_chrome_session(profile)

        except Exception as e:
            terminal_print(f"Erreur copen : {type(e).__name__}: {e}", "#ff5555")

    threading.Thread(target=worker, daemon=True).start()


# ============================================================
# COMMANDE TIKTOK
# ============================================================

def cmd_tik(args):
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
        terminal_print(f"❌ Fichier introuvable : {video_path}", "#ff4444")
        return

    hashtags = [tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]

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

            terminal_print(f"Lancement de Chrome : {profile_name}", "#00aaff")

            driver = connect_selenium(profile_name, URL)
            if driver is None:
                return

            wait = WebDriverWait(driver, 40)

            terminal_print("✅ Selenium connecté !", "#00ff88")

            driver.get(URL)

            terminal_print("Recherche du bouton vidéo...", "#00aaff")

            bouton = wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "button.upload-stage-btn.Button__root.Button__root--shape-default."
                    "Button__root--size-large.Button__root--type-primary"
                ))
            )

            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", bouton
            )
            time.sleep(1)

            ActionChains(driver).move_to_element(bouton).pause(0.5).click().perform()

            terminal_print("✅ Bouton cliqué !", "#00ff88")

            time.sleep(2)

            terminal_print("Sélection de la vidéo...", "#00aaff")

            pyperclip.copy(os.path.normpath(video_path))
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.5)
            pyautogui.press("enter")

            terminal_print("✅ Chemin de la vidéo envoyé.", "#00ff88")

            terminal_print("Attente du chargement de la vidéo...", "#00aaff")
            time.sleep(5)

            terminal_print("Recherche du champ de description...", "#00aaff")

            description = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[contenteditable="true"]'))
            )

            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", description
            )
            time.sleep(1)

            ActionChains(driver).move_to_element(description).pause(0.3).click().perform()
            time.sleep(0.5)

            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.3)

            pyperclip.copy(full_description)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.5)

            terminal_print("✅ Description et hashtags saisis !", "#00ff88")
            terminal_print(f"Description : {description_text}", "#cccccc")

            if hashtags:
                terminal_print("Hashtags : " + " ".join(hashtags), "#cccccc")

            terminal_print("📝 Vérifie la description dans TikTok avant publication.", "#00aaff")

        except Exception as e:
            terminal_print(f"❌ Erreur TikTok : {e}", "#ff4444")

    threading.Thread(target=worker, daemon=True).start()


# ============================================================
# GOOGLE FLOW : projet
# ============================================================

def cmd_cresce(args):
    if len(args) not in (1, 2):
        terminal_print('Usage : cresce "Profil" ["URL_PROJET_FLOW"]', "#ffaa00")
        return

    profile = args[0].strip().strip('"')
    try:
        if len(args) == 2:
            project_url = set_flow_project_url(profile, args[1].strip().strip('"'))
            terminal_print(f"Projet Flow enregistré pour {profile}.", "#55ff55")
        else:
            project_url = get_flow_project_url(profile) or FLOW_HOME

        if not launch_chrome_session(profile, project_url):
            return

        port = int(load_chrome_sessions()[profile]["port"])
        terminal_print(f"Chrome connecté sur le port {port}.", "#55ff55")
        terminal_print("URL : " + project_url, "#55aaff")
        if project_url == FLOW_HOME:
            terminal_print(
                "Ouvre ou crée ton projet Flow, puis tape : cproject " + profile,
                "#ffaa00"
            )
    except Exception as exc:
        terminal_print(f"Erreur Chrome : {type(exc).__name__}: {exc}", "#ff5555")


def cmd_cproject(args):
    if len(args) != 1:
        terminal_print('Usage : cproject "Profil"', "#ffaa00")
        return

    profile = args[0].strip().strip('"')
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        session = ensure_chrome_session(profile)
        if not chrome_session_running(int(session["port"])):
            terminal_print(f"Le profil {profile} n'est pas ouvert. Lance cresce {profile}.", "#ff5555")
            return

        options = Options()
        options.add_experimental_option(
            "debuggerAddress", f"127.0.0.1:{int(session['port'])}"
        )
        driver = webdriver.Chrome(options=options)
        try:
            current_url = driver.current_url
            if "flow.google.com/project/" not in current_url:
                for handle in driver.window_handles:
                    driver.switch_to.window(handle)
                    if "flow.google.com/project/" in driver.current_url:
                        current_url = driver.current_url
                        break
            saved_url = set_flow_project_url(profile, current_url)
            terminal_print(f"Projet Flow enregistré pour {profile} : {saved_url}", "#55ff55")
        finally:
            # driver.quit() fermerait Chrome ; on ne le fait pas
            pass
    except Exception as exc:
        terminal_print(f"Impossible d'enregistrer le projet : {exc}", "#ff5555")


def configure_flow_settings(driver, log, mode_icon, outputs, ratio="9:16",
                            type_icon=None, model_keyword=None, timeout=20):
    """Force les réglages Google Flow, indépendamment de la langue / du compte.

    Les boutons sont repérés par leur icône (image, videocam, chrome_extension) ou
    leur texte universel (9:16, x1, x3), jamais par des libellés traduits.
    - mode_icon : "image" ou "videocam"
    - type_icon : icône du type de vidéo (ex. "chrome_extension" = Ingrédients)
    - model_keyword : si fourni, tente de sélectionner ce modèle (non bloquant)
    """
    from selenium.common.exceptions import (
        StaleElementReferenceException, NoSuchElementException
    )
    from selenium.webdriver.common.action_chains import ActionChains

    wait = WebDriverWait(driver, timeout)
    root_xp = '//flow-prompt-box-settings'

    def by_icon(icon):
        return (f'{root_xp}//mat-button-toggle[.//mat-icon[normalize-space()="{icon}"]]'
                f'/button[@role="radio"]')

    def by_text(text):
        return (f'{root_xp}//mat-button-toggle[.//span[contains(@class,"toggle-text") '
                f'and normalize-space()="{text}"]]/button[@role="radio"]')

    targets = [("mode", by_icon(mode_icon))]
    if type_icon:
        targets.append(("type", by_icon(type_icon)))
    targets.append(("format", by_text(ratio)))
    targets.append(("sorties", by_text(outputs)))

    def panel_open():
        try:
            return any(e.is_displayed() for e in driver.find_elements(
                By.XPATH, f'{root_xp}//mat-button-toggle'))
        except Exception:
            return False

    def open_panel():
        if panel_open():
            return
        btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.settings-trigger-button")))
        driver.execute_script("arguments[0].click();", btn)
        wait.until(lambda d: panel_open())
        time.sleep(0.6)

    def close_panel():
        if panel_open():
            try:
                btn = driver.find_element(By.CSS_SELECTOR, "button.settings-trigger-button")
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.5)
            except Exception:
                pass

    def is_checked(xp):
        try:
            return driver.find_element(By.XPATH, xp).get_attribute("aria-checked") == "true"
        except (NoSuchElementException, StaleElementReferenceException):
            return False

    def select(name, xp):
        last = None
        for i in range(6):
            try:
                if is_checked(xp):
                    return
                btn = driver.find_element(By.XPATH, xp)
                if i % 2 == 0:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});"
                        "arguments[0].click();", btn)
                else:  # clic « réel » si le clic JS n'a pas suffi
                    ActionChains(driver).move_to_element(btn).click().perform()
                time.sleep(0.8)
                if is_checked(xp):
                    return
            except (NoSuchElementException, StaleElementReferenceException) as e:
                last = e
                time.sleep(0.6)
        raise Exception(f"réglage « {name} » introuvable ou non sélectionnable ({last})")

    def find_model_button():
        for css in [
            'button[aria-label="Sélectionner une famille de modèles"]',
            f'{root_xp.replace("//", "")} button.mat-mdc-menu-trigger',
            f'{root_xp.replace("//", "")} button[aria-haspopup="menu"]',
        ]:
            for el in driver.find_elements(By.CSS_SELECTOR, css):
                try:
                    if el.is_displayed():
                        return el
                except StaleElementReferenceException:
                    continue
        return None

    def model_text():
        el = find_model_button()
        try:
            return (el.text or "").strip() if el is not None else ""
        except StaleElementReferenceException:
            return ""

    def select_model():
        key = model_keyword.lower()
        if key in model_text().lower():
            return
        btn = find_model_button()
        if btn is None:
            raise Exception("bouton du modèle introuvable")
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(0.8)
        for opt in driver.find_elements(
            By.XPATH,
            '//div[contains(@class,"mat-mdc-menu-panel")]'
            '//*[self::button or @role="menuitem" or @role="menuitemradio" or @role="option"]'
        ):
            try:
                if key in " ".join((opt.text or "").split()).lower() and opt.is_displayed():
                    driver.execute_script("arguments[0].click();", opt)
                    time.sleep(1)
                    return
            except StaleElementReferenceException:
                continue
        raise Exception(f"modèle « {model_keyword} » introuvable dans le menu")

    def apply_all():
        open_panel()
        select("mode", targets[0][1])
        time.sleep(1)  # Flow redessine le panneau après le changement de mode
        open_panel()
        for name, xp in targets[1:]:
            select(name, xp)

    def verify():
        return [name for name, xp in targets if not is_checked(xp)]

    last_error = None
    for attempt in range(1, 4):
        try:
            apply_all()
            bad = verify()
            if not bad:
                if model_keyword:
                    try:
                        select_model()
                    except Exception as e:
                        log(f"Modèle non modifié : {e}", "#ffaa00")
                log(f"Configuration validée : {mode_icon}, {ratio}, {outputs}"
                    + (f", {model_text()}" if model_keyword else "") + ".", "#55ff55")
                close_panel()
                return
            last_error = Exception("non confirmés : " + ", ".join(bad))
        except Exception as e:
            last_error = e
        log(f"Réglages Flow : tentative {attempt}/3 échouée ({last_error}).", "#ffaa00")
        time.sleep(1)

    try:
        html = driver.execute_script(
            "const p=document.querySelector('flow-prompt-box-settings');"
            "return p?p.outerHTML:document.body.outerHTML;")
        dump = Path.cwd() / f"flow_debug_{mode_icon}.html"
        dump.write_text(html or "", encoding="utf-8")
        log(f"HTML du panneau sauvegardé : {dump}", "#ffaa00")
    except Exception:
        pass
    raise Exception(f"Configuration Flow impossible ({mode_icon}) : {last_error}")


# ============================================================
# gen_image
# ============================================================

def cmd_gen_image(args):

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
        try:
            log(f"Vérification du profil Chrome : {profile_name}", "#55aaff")

            project_url = get_flow_project_url(profile_name)
            if not project_url:
                log(f"Aucun projet Flow enregistré pour {profile_name}. "
                    f"Lance cresce {profile_name}, ouvre ton projet puis tape "
                    f"cproject {profile_name}.", "#ff5555")
                return

            driver = connect_selenium(profile_name, project_url, log)
            if driver is None:
                return

            log("Selenium connecté !", "#55ff55")

            if not ensure_flow_project_tab(driver, profile_name, log):
                return

            wait = WebDriverWait(driver, 20)

            log("Configuration du mode image...", "#55aaff")
            configure_flow_settings(driver, log, "image", "x3")

            selector = (
                "flow-rich-text-editor.prompt-input "
                "[role='textbox'][contenteditable='true']"
            )

            for index, prompt in enumerate(prompts, start=1):
                log(f"[{index}/{len(prompts)}] Recherche du champ...", "#ffaa00")

                try:
                    editor = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )

                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", editor
                    )

                    editor.click()
                    editor.send_keys(Keys.CONTROL, "a")
                    editor.send_keys(Keys.BACKSPACE)
                    editor.send_keys(prompt)

                    time.sleep(0.5)

                    current_text = (
                        editor.get_attribute("innerText") or editor.text or ""
                    )

                    if prompt.strip() not in current_text:
                        log("Le texte n'est pas confirmé dans le champ.", "#ff5555")
                        return

                    log(f"[{index}/{len(prompts)}] Texte saisi et vérifié.", "#55ff55")

                    generate_button = driver.find_element(
                        By.CSS_SELECTOR, "button.generate-icon-button"
                    )

                    if not generate_button.is_enabled():
                        log("Le bouton de génération est désactivé.", "#ff5555")
                        return

                    generate_button.click()

                    log(f"[{index}/{len(prompts)}] Génération lancée : 3 images.", "#55ff55")

                except Exception as exc:
                    log(f"Erreur au prompt {index} : {type(exc).__name__}: {exc}", "#ff5555")
                    return

                if index < len(prompts):
                    log("Attente de 60 secondes avant le prochain prompt...", "#ffaa00")
                    time.sleep(60)
                else:
                    # Dernier prompt : on laisse Flow finir de générer, sinon la
                    # commande suivante d'un script CD (save...) partirait trop tôt.
                    log("Attente de 60 secondes : fin de la génération...", "#ffaa00")
                    time.sleep(60)

            log("Tous les prompts ont été traités !", "#55ff55")

        except Exception as exc:
            log(f"Erreur gen_image : {type(exc).__name__}: {exc}", "#ff5555")

    threading.Thread(target=worker, daemon=True).start()


def ensure_flow_project_tab(driver, profile, say):
    """Se place sur l'onglet du projet Flow ; l'ouvre depuis l'URL mémorisée si besoin."""
    for handle in driver.window_handles:
        try:
            driver.switch_to.window(handle)
            if "flow.google.com/project/" in driver.current_url:
                return True
        except Exception:
            continue

    project_url = get_flow_project_url(profile)
    if not project_url:
        say(
            f"Aucun projet Flow enregistré pour {profile}. "
            f"Ouvre ton projet puis tape : cproject {profile}"
        )
        return False

    say("Ouverture du projet Flow...")
    driver.switch_to.window(driver.window_handles[0])
    driver.get(project_url)
    try:
        WebDriverWait(driver, 40).until(
            lambda d: "flow.google.com/project/" in d.current_url
        )
    except Exception:
        say(
            "Le projet Flow ne s'ouvre pas (compte Google non connecté dans "
            f"la session {profile} ?). Page actuelle : {driver.current_url}"
        )
        return False
    try:
        WebDriverWait(driver, 30).until(
            lambda d: d.find_elements(
                By.CSS_SELECTOR,
                "flow-grid-tile-container, flow-image-tile, flow-video-tile"
            )
        )
    except Exception:
        pass
    time.sleep(2)
    return True


# ============================================================
# save : sauvegarde TOUTES les images ET vidéos du projet Flow
# ============================================================
# Utilisation :
#   save                         -> profil par défaut, dossier "flow_media"
#   save "Profil"                -> ce profil, dossier "flow_media"
#   save "Profil" "C:\Mes\Medias"
#   save "C:\Mes\Medias"         -> si le 1er argument n'est pas un profil connu,
#                                   il est pris comme dossier
#
# Nommage :
#   - images converties en JPG : scene_1_A.jpg, scene_1_B.jpg, scene_1_C.jpg,
#     scene_2_A.jpg, ...  (3 images par scène, comme gen_image)
#   - vidéos : video_scene_1.mp4, video_scene_2.mp4, ...
#   - un fichier _index.json dans le dossier retient quel média a quel nom :
#     relancer save ne renomme rien et continue la numérotation.
#   - nécessite Pillow pour la conversion JPG : pip install pillow

# Mets False si la galerie Flow affiche les plus anciens médias en premier.
GALLERY_NEWEST_FIRST = True
IMAGES_PER_SCENE = 3

# Fonction JS réutilisable : trouve l'élément qui défile réellement
_FLOW_SCROLLER_JS = """
function scroller() {
    const c = [document.querySelector('[cdkvirtualscrollingelement]'),
               document.querySelector('.cdk-virtual-scrollable'),
               document.querySelector('cdk-virtual-scroll-viewport'),
               document.scrollingElement];
    for (const e of c) if (e && e.scrollHeight > e.clientHeight + 2) return e;
    return c.find(Boolean);
}
"""

# Script JS : liste les médias actuellement présents dans le DOM
_FLOW_COLLECT_JS = """
const out = [];
document.querySelectorAll('flow-grid-tile-container').forEach(c => {
    const title = c.getAttribute('aria-label') || '';
    const img = c.querySelector('flow-image-tile img[data-media-id]');
    if (img) {
        const url = img.currentSrc || img.src;
        if (url && !url.startsWith('data:')) {
            out.push({type: 'image',
                      id: img.getAttribute('data-media-id'),
                      url: url, thumb: '', title: title,
                      key: img.getAttribute('data-media-id')});
        }
        return;
    }
    const vt = c.querySelector('flow-video-tile');
    if (vt) {
        const v = vt.querySelector('video');
        const th = vt.querySelector('img.thumbnail');
        const thumb = th ? (th.currentSrc || th.src) : '';
        const url = v ? (v.currentSrc || v.src || v.getAttribute('src') || '') : '';
        const key = 'v:' + (thumb || title);
        c.setAttribute('data-flow-key', key);
        out.push({type: 'video', id: '', url: url, thumb: thumb,
                  title: title, key: key});
    }
});
return out;
"""

# Script JS : télécharge une URL depuis la page et renvoie du base64
_FLOW_FETCH_JS = """
const url = arguments[0];
const done = arguments[arguments.length - 1];
fetch(url, {credentials: 'include'})
  .then(r => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const ct = r.headers.get('Content-Type') || '';
      return r.blob().then(b => ({b: b, ct: ct}));
  })
  .then(o => {
      const fr = new FileReader();
      fr.onloadend = () => done({ok: true, ct: o.ct,
                                 data: String(fr.result).split(',')[1] || ''});
      fr.onerror = () => done({ok: false, err: 'lecture du blob impossible'});
      fr.readAsDataURL(o.b);
  })
  .catch(e => done({ok: false, err: String(e)}));
"""


def _flow_ext(data, content_type, media_type):
    """Déduit l'extension d'après le contenu réel, puis le Content-Type."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if data[4:8] == b"ftyp":
        return ".mp4"
    if data[:4] == b"\x1aE\xdf\xa3":
        return ".webm"

    ct = (content_type or "").lower()
    for key, ext in (
        ("image/png", ".png"), ("image/jpeg", ".jpg"), ("image/webp", ".webp"),
        ("image/gif", ".gif"), ("video/mp4", ".mp4"), ("video/webm", ".webm"),
    ):
        if key in ct:
            return ext

    return ".mp4" if media_type == "video" else ".jpg"


def _flow_media_name(item):
    """Identifiant stable (sans extension) pour une image ou une vidéo.

    Sert de clé dans _index.json. Pour les vidéos on se base sur la miniature
    (stable) plutôt que sur l'URL de la vidéo, qui peut être signée et changer
    d'une session à l'autre.
    """
    if item["id"]:
        return item["id"]
    base = item.get("thumb") or item.get("title") or item["url"]
    digest = _hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]
    return f"video_{digest}"


def _to_jpg_bytes(data):
    """Convertit n'importe quelle image (WEBP, PNG...) en JPG. None si impossible."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        if img.mode in ("RGBA", "LA", "P"):
            rgba = img.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, "JPEG", quality=95)
        return out.getvalue()
    except Exception:
        return None


def _flow_resolve_video_url(driver, key):
    """La balise <video> n'existe qu'au survol / à l'ouverture : on la déclenche."""
    from selenium.webdriver.common.action_chains import ActionChains

    tile = None
    for c in driver.find_elements(By.CSS_SELECTOR, "flow-grid-tile-container[data-flow-key]"):
        if c.get_attribute("data-flow-key") == key:
            tile = c
            break
    if tile is None:
        return ""

    tile_video_js = (
        "const v = arguments[0].querySelector('video');"
        "return v ? (v.currentSrc || v.src || v.getAttribute('src') || '') : '';"
    )

    # 1) survol de la tuile
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tile)
        ActionChains(driver).move_to_element(tile).perform()
        for _ in range(8):
            time.sleep(0.4)
            url = driver.execute_script(tile_video_js, tile)
            if url:
                return url
    except Exception:
        pass

    # 2) ouverture de la vidéo, lecture de l'URL, puis retour
    try:
        before = driver.current_url
        driver.execute_script(
            "arguments[0].querySelector('flow-video-tile').click();", tile
        )
        url = ""
        for _ in range(20):
            time.sleep(0.5)
            url = driver.execute_script(
                "const v = document.querySelector('video');"
                "return v ? (v.currentSrc || v.src || v.getAttribute('src') || '') : '';"
            )
            if url:
                break
        if driver.current_url != before:
            driver.back()
            time.sleep(2)
        else:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(1)
        return url or ""
    except Exception:
        return ""


def _flow_dump(driver, name, log):
    """Sauvegarde la page pour diagnostiquer un sélecteur introuvable."""
    try:
        dump = Path.cwd() / f"flow_debug_{name}.html"
        dump.write_text(driver.page_source or "", encoding="utf-8")
        log(f"Page sauvegardée pour diagnostic : {dump}", "#ffaa00")
    except Exception:
        pass


def _flow_collect_all(driver, log):
    """Fait défiler le vrai conteneur de scroll et résout les URL des vidéos."""
    found = {}

    def harvest():
        for item in driver.execute_script(_FLOW_COLLECT_JS) or []:
            key = item["key"] or item["url"]
            if key not in found:
                found[key] = item
            if item["type"] == "video" and not found[key]["url"]:
                url = _flow_resolve_video_url(driver, key)
                if url:
                    found[key]["url"] = url

    def metrics():
        return driver.execute_script(_FLOW_SCROLLER_JS + """
            const s = scroller();
            return s ? {top: s.scrollTop, height: s.clientHeight,
                        total: s.scrollHeight} : null;
        """)

    def scroll_top():
        driver.execute_script(_FLOW_SCROLLER_JS + """
            const s = scroller(); if (s) s.scrollTop = 0;
        """)

    def scroll_down():
        driver.execute_script(_FLOW_SCROLLER_JS + """
            const s = scroller();
            if (s) s.scrollTop = s.scrollTop + Math.max(120, s.clientHeight * 0.7);
        """)

    scroll_top()
    time.sleep(1.2)

    stalls = 0
    for _ in range(600):
        harvest()
        m = metrics()
        if m is None:
            break

        at_bottom = m["top"] + m["height"] >= m["total"] - 2
        if at_bottom:
            # La galerie peut charger d'autres lignes en bas : on re-vérifie
            time.sleep(1.5)
            harvest()
            m2 = metrics()
            if m2 is None or m2["total"] <= m["total"]:
                break
            stalls += 1
            if stalls > 50:
                break
            continue

        scroll_down()
        time.sleep(0.9)

    harvest()
    items = list(found.values())

    no_url = [i for i in items if not i["url"]]
    if no_url:
        log(f"{len(no_url)} média(s) sans URL (ignorés).", "#ffaa00")
        _flow_dump(driver, "save_nourl", log)

    return [i for i in items if i["url"]]


def cmd_save(args):

    # ---- Lecture des arguments : [profil] [dossier] ----
    args = [a.strip().strip('"') for a in args]
    sessions = load_chrome_sessions()

    profile_arg = None
    folder_arg = None

    if len(args) >= 2:
        profile_arg, folder_arg = args[0], args[1]
    elif len(args) == 1:
        if args[0] in sessions:
            profile_arg = args[0]
        else:
            folder_arg = args[0]

    folder = Path(folder_arg) if folder_arg else Path("flow_media")

    def log(message, color=None):
        try:
            root.after(0, lambda m=message, c=color: terminal_print(m, c))
        except Exception:
            print(message)

    def worker():
        try:
            selected_profile = profile_arg or get_default_chrome_profile()
            log(f"Profil : {selected_profile}", "#55aaff")

            driver = connect_selenium(
                selected_profile,
                get_flow_project_url(selected_profile) or "about:blank",
                log
            )
            if driver is None:
                return
            driver.set_script_timeout(180)

            if not ensure_flow_project_tab(driver, selected_profile, log):
                return

            folder.mkdir(parents=True, exist_ok=True)

            log("Parcours de la galerie Flow (images + vidéos)...", "#ffaa00")
            items = _flow_collect_all(driver, log)

            images = [i for i in items if i["type"] == "image"]
            videos = [i for i in items if i["type"] == "video"]
            log(f"{len(items)} média(s) trouvé(s) : {len(images)} image(s), "
                f"{len(videos)} vidéo(s).", "#55ff55")

            if not items:
                log("Rien à sauvegarder.", "#ffaa00")
                _flow_dump(driver, "save_empty", log)
                return

            # Ordre chronologique : le plus ancien (scène 1) en premier
            if GALLERY_NEWEST_FIRST:
                images.reverse()
                videos.reverse()
            ordered = images + videos

            # ---- Index des médias déjà sauvegardés ----
            index_path = folder / "_index.json"
            try:
                manifest = json.loads(index_path.read_text(encoding="utf-8"))
            except Exception:
                manifest = {}
            # on oublie les entrées dont le fichier a été supprimé
            manifest = {k: v for k, v in manifest.items()
                        if (folder / v["file"]).exists()}

            count = {
                "image": sum(1 for v in manifest.values() if v["type"] == "image"),
                "video": sum(1 for v in manifest.values() if v["type"] == "video"),
            }

            # Session requests de secours (cookies + User-Agent du navigateur)
            fallback = None

            def get_fallback():
                nonlocal fallback
                if fallback is None:
                    import requests
                    fallback = requests.Session()
                    for ck in driver.get_cookies():
                        fallback.cookies.set(
                            ck["name"], ck["value"],
                            domain=ck.get("domain"), path=ck.get("path", "/")
                        )
                    fallback.headers.update({
                        "User-Agent": driver.execute_script("return navigator.userAgent"),
                        "Referer": driver.current_url,
                    })
                return fallback

            saved = skipped = failed = 0

            for n, item in enumerate(ordered, 1):
                key = _flow_media_name(item)
                kind = item["type"]
                label = "vidéo" if kind == "video" else "image"

                if key in manifest:
                    skipped += 1
                    log(f"[{n}/{len(ordered)}] {label} déjà présente : "
                        f"{manifest[key]['file']}", "#888888")
                    continue

                # Nom visé selon la position
                pos = count[kind]
                if kind == "image":
                    scene = pos // IMAGES_PER_SCENE + 1
                    letter = chr(ord("A") + pos % IMAGES_PER_SCENE)
                    base = f"scene_{scene}_{letter}"
                else:
                    base = f"video_scene_{pos + 1}"

                data = None
                content_type = ""
                last_err = None

                # 1) téléchargement depuis la page
                try:
                    res = driver.execute_async_script(_FLOW_FETCH_JS, item["url"])
                    if res and res.get("ok") and res.get("data"):
                        data = _b64.b64decode(res["data"])
                        content_type = res.get("ct", "")
                    else:
                        last_err = (res or {}).get("err", "réponse vide")
                except Exception as exc:
                    last_err = exc

                # 2) secours : requests
                if not data:
                    try:
                        resp = get_fallback().get(item["url"], timeout=120)
                        resp.raise_for_status()
                        data = resp.content
                        content_type = resp.headers.get("Content-Type", "")
                    except Exception as exc:
                        last_err = f"{last_err} | requests : {exc}"

                if not data:
                    failed += 1
                    log(f"[{n}/{len(ordered)}] Échec {label} {base} : {last_err}", "#ff5555")
                    continue

                if kind == "image":
                    jpg = _to_jpg_bytes(data)
                    if jpg is not None:
                        data, ext = jpg, ".jpg"
                    else:
                        ext = _flow_ext(data, content_type, kind)
                        log("Conversion JPG impossible (pip install pillow ?) : "
                            f"fichier gardé en {ext}", "#ffaa00")
                else:
                    ext = _flow_ext(data, content_type, kind)

                path = folder / (base + ext)
                path.write_bytes(data)
                manifest[key] = {"file": path.name, "type": kind}
                count[kind] += 1
                index_path.write_text(
                    json.dumps(manifest, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                saved += 1
                log(f"[{n}/{len(ordered)}] {label} sauvegardée : "
                    f"{path.name} ({len(data) / 1024:,.0f} Ko)", "#55ff55")

            log("", None)
            log("==============================", "#00ff88")
            log("SAUVEGARDE TERMINÉE", "#00ff88")
            log(f"Nouveaux fichiers : {saved}", "#55ff55")
            log(f"Déjà présents     : {skipped}", "#aaaaaa")
            log(f"Échecs            : {failed}", "#ff5555" if failed else "#aaaaaa")
            log(f"Dossier : {folder.resolve()}", "#55aaff")
            log("==============================", "#00ff88")

        except Exception as exc:
            log(f"Erreur save : {type(exc).__name__}: {exc}", "#ff5555")

        # Selenium est attaché à une session Chrome existante : on ne la ferme pas.

    threading.Thread(target=worker, daemon=True).start()


# ============================================================
# save_video : sauvegarde UNIQUEMENT les vidéos de Flow
# ============================================================
# Utilisation :
#   save_video                  -> profil par défaut, dossier "video"
#   save_video profil           -> ce profil Chrome, dossier "video"
#   save_video profil dossier   -> ce profil, un autre dossier
#
# Les fichiers sont numérotés dans l'ordre chronologique : 1.mp4, 2.mp4, 3.mp4...
# Si le dossier contient déjà 1.mp4 et 2.mp4, la prochaine vidéo sera 3.mp4.

VIDEO_FOLDER = "video"


def _flow_next_video_number(folder):
    """Plus grand numéro déjà utilisé dans le dossier, + 1 (1 si le dossier est vide)."""
    used = [int(p.stem) for p in folder.iterdir()
            if p.is_file() and p.stem.isdigit()]
    return max(used, default=0) + 1


def cmd_save_video(args):
    args = [a.strip().strip('"') for a in args]
    sessions = load_chrome_sessions()

    profile_arg = None
    folder_arg = None

    if len(args) >= 2:
        profile_arg, folder_arg = args[0], args[1]
    elif len(args) == 1:
        if args[0] in sessions:
            profile_arg = args[0]
        else:
            folder_arg = args[0]

    folder = Path(folder_arg) if folder_arg else Path(VIDEO_FOLDER)

    def log(message, color=None):
        try:
            root.after(0, lambda m=message, c=color: terminal_print(m, c))
        except Exception:
            print(message)

    def worker():
        try:
            selected_profile = profile_arg or get_default_chrome_profile()
            log(f"Profil : {selected_profile}", "#55aaff")

            driver = connect_selenium(
                selected_profile,
                get_flow_project_url(selected_profile) or "about:blank",
                log
            )
            if driver is None:
                return
            driver.set_script_timeout(180)

            if not ensure_flow_project_tab(driver, selected_profile, log):
                return

            folder.mkdir(parents=True, exist_ok=True)

            log("Parcours de la galerie Flow (vidéos uniquement)...", "#ffaa00")
            items = _flow_collect_all(driver, log)
            videos = [i for i in items if i["type"] == "video"]
            log(f"{len(videos)} vidéo(s) trouvée(s).", "#55ff55")

            if not videos:
                log("Aucune vidéo à sauvegarder.", "#ffaa00")
                _flow_dump(driver, "save_video_empty", log)
                return

            # Ordre chronologique : la plus ancienne = 1
            if GALLERY_NEWEST_FIRST:
                videos.reverse()

            # Une même vidéo peut être relevée deux fois (clé de miniature qui
            # change pendant le défilement) : on retire les URL identiques,
            # en ignorant les paramètres de signature (?...).
            seen_urls = set()
            unique = []
            for v in videos:
                base_url = v["url"].split("?", 1)[0]
                if base_url in seen_urls:
                    continue
                seen_urls.add(base_url)
                unique.append(v)
            if len(unique) < len(videos):
                log(f"{len(videos) - len(unique)} doublon(s) d'URL ignoré(s).", "#888888")
            videos = unique

            # ---- Index des vidéos déjà sauvegardées ----
            index_path = folder / "_index.json"
            try:
                manifest = json.loads(index_path.read_text(encoding="utf-8"))
            except Exception:
                manifest = {}
            manifest = {k: v for k, v in manifest.items()
                        if (folder / v["file"]).exists()}

            fallback = None

            def get_fallback():
                nonlocal fallback
                if fallback is None:
                    import requests
                    fallback = requests.Session()
                    for ck in driver.get_cookies():
                        fallback.cookies.set(
                            ck["name"], ck["value"],
                            domain=ck.get("domain"), path=ck.get("path", "/")
                        )
                    fallback.headers.update({
                        "User-Agent": driver.execute_script("return navigator.userAgent"),
                        "Referer": driver.current_url,
                    })
                return fallback

            # Empreinte (SHA-1) du contenu de chaque vidéo déjà dans le dossier :
            # garantit qu'un même fichier n'est jamais enregistré deux fois.
            known_hashes = {}
            for existing in folder.iterdir():
                if existing.is_file() and existing.stem.isdigit():
                    try:
                        digest = _hashlib.sha1(existing.read_bytes()).hexdigest()
                        known_hashes.setdefault(digest, existing.name)
                    except OSError:
                        pass

            saved = skipped = failed = 0
            next_number = _flow_next_video_number(folder)

            for n, item in enumerate(videos, 1):
                key = _flow_media_name(item)

                if key in manifest:
                    skipped += 1
                    log(f"[{n}/{len(videos)}] vidéo déjà présente : "
                        f"{manifest[key]['file']}", "#888888")
                    continue

                data = None
                content_type = ""
                last_err = None

                # 1) téléchargement depuis la page
                try:
                    res = driver.execute_async_script(_FLOW_FETCH_JS, item["url"])
                    if res and res.get("ok") and res.get("data"):
                        data = _b64.b64decode(res["data"])
                        content_type = res.get("ct", "")
                    else:
                        last_err = (res or {}).get("err", "réponse vide")
                except Exception as exc:
                    last_err = exc

                # 2) secours : requests
                if not data:
                    try:
                        resp = get_fallback().get(item["url"], timeout=120)
                        resp.raise_for_status()
                        data = resp.content
                        content_type = resp.headers.get("Content-Type", "")
                    except Exception as exc:
                        last_err = f"{last_err} | requests : {exc}"

                if not data:
                    failed += 1
                    log(f"[{n}/{len(videos)}] Échec vidéo : {last_err}", "#ff5555")
                    continue

                digest = _hashlib.sha1(data).hexdigest()
                if digest in known_hashes:
                    skipped += 1
                    # on mémorise la clé pour ne pas la retélécharger la prochaine fois
                    manifest[key] = {"file": known_hashes[digest], "type": "video"}
                    index_path.write_text(
                        json.dumps(manifest, indent=2, ensure_ascii=False),
                        encoding="utf-8"
                    )
                    log(f"[{n}/{len(videos)}] doublon ignoré (identique à "
                        f"{known_hashes[digest]})", "#888888")
                    continue

                ext = _flow_ext(data, content_type, "video")
                path = folder / f"{next_number}{ext}"
                known_hashes[digest] = path.name
                path.write_bytes(data)
                manifest[key] = {"file": path.name, "type": "video"}
                index_path.write_text(
                    json.dumps(manifest, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                next_number += 1
                saved += 1
                log(f"[{n}/{len(videos)}] vidéo sauvegardée : "
                    f"{path.name} ({len(data) / 1024:,.0f} Ko)", "#55ff55")

            log("", None)
            log("==============================", "#00ff88")
            log("SAUVEGARDE VIDÉO TERMINÉE", "#00ff88")
            log(f"Nouvelles vidéos : {saved}", "#55ff55")
            log(f"Déjà présentes   : {skipped}", "#aaaaaa")
            log(f"Échecs           : {failed}", "#ff5555" if failed else "#aaaaaa")
            log(f"Dossier : {folder.resolve()}", "#55aaff")
            log("==============================", "#00ff88")

        except Exception as exc:
            log(f"Erreur save_video : {type(exc).__name__}: {exc}", "#ff5555")

    threading.Thread(target=worker, daemon=True).start()


# ============================================================
# delflow
# ============================================================

def cmd_delflow(args):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import (
        NoSuchElementException,
        StaleElementReferenceException,
        TimeoutException
    )

    def worker():
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

            selected_profile = args[1] if len(args) > 1 else get_default_chrome_profile()
            driver = connect_selenium(
                selected_profile,
                get_flow_project_url(selected_profile) or "about:blank"
            )
            if driver is None:
                return

            if not ensure_flow_project_tab(driver, selected_profile, terminal_print):
                return

            wait = WebDriverWait(driver, 10)

            time.sleep(3)

            def scroll_to_top():
                driver.execute_script(_FLOW_SCROLLER_JS + """
                    const s = scroller(); if (s) s.scrollTop = 0;
                """)

            scroll_to_top()
            time.sleep(2)

            def tag_menus():
                # Repère les boutons « ⋮ » par leur icône (indépendant de la langue du compte)
                driver.execute_script("""
                    document.querySelectorAll('button[aria-haspopup="menu"]').forEach(b => {
                        const i = b.querySelector('mat-icon');
                        if (i && i.textContent.trim() === 'more_vert') {
                            b.setAttribute('data-flow-more', '1');
                        }
                    });
                """)

            def get_first_tile():
                tag_menus()
                return driver.execute_script("""
                    const image = [...document.querySelectorAll(
                        'img[data-media-id]'
                    )].find(el => el.closest(
                        'flow-image-tile'
                    )?.closest('flow-grid-tile-container')?.querySelector(
                        'button[data-flow-more="1"]'
                    ));

                    if (image) {
                        return {
                            id: image.getAttribute('data-media-id'),
                            type: 'image'
                        };
                    }

                    const video = [...document.querySelectorAll(
                        'flow-video-tile'
                    )].find(el => el.closest(
                        'flow-grid-tile-container'
                    )?.querySelector(
                        'button[data-flow-more="1"]'
                    ));

                    if (video) {
                        const c = video.closest('flow-grid-tile-container');
                        const th = video.querySelector('img.thumbnail');
                        const key = 'v:' + ((th && (th.currentSrc || th.src)) ||
                                            c.getAttribute('aria-label') || '');
                        c.setAttribute('data-flow-key', key);
                        return { id: key, type: 'video' };
                    }

                    return null;
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
                    terminal_print("Aucun autre média détecté en haut de la galerie.")
                    break

                media_id = tile_data["id"]

                try:
                    if tile_data["type"] == "image":
                        element = driver.find_element(
                            By.CSS_SELECTOR, f'img[data-media-id="{media_id}"]'
                        )
                        tile = driver.execute_script(
                            "return arguments[0].closest('flow-grid-tile-container');",
                            element
                        )
                    else:
                        tile = next(
                            el for el in driver.find_elements(
                                By.CSS_SELECTOR,
                                "flow-grid-tile-container[data-flow-key]"
                            ) if el.get_attribute("data-flow-key") == media_id
                        )

                    tag_menus()

                    menu_button = tile.find_element(
                        By.CSS_SELECTOR, 'button[data-flow-more="1"]'
                    )

                    driver.execute_script("arguments[0].click();", menu_button)

                    menu = wait.until(
                        lambda d: d.find_element(By.CSS_SELECTOR, '[role="menu"]')
                    )

                    delete_button = menu.find_element(
                        By.XPATH,
                        ".//button[@role='menuitem' and "
                        ".//mat-icon[normalize-space()='delete']]"
                    )

                    delete_button.click()

                    # Attendre que le média disparaisse
                    WebDriverWait(driver, 10).until(
                        lambda d: not d.execute_script("""
                            if (arguments[1] === 'image') {
                                return [...document.querySelectorAll(
                                    'img[data-media-id]'
                                )].some(el =>
                                    el.getAttribute('data-media-id') === arguments[0]
                                );
                            }
                            return [...document.querySelectorAll(
                                'flow-grid-tile-container[data-flow-key]'
                            )].some(el =>
                                el.getAttribute('data-flow-key') === arguments[0]
                            );
                        """, media_id, tile_data["type"])
                    )

                    deleted += 1
                    errors = 0

                    terminal_print(
                        f"[SUPPRIMÉ] {media_id} | Total : {deleted}",
                        color="#55ff55"
                    )

                    time.sleep(0.4)

                except StaleElementReferenceException:
                    continue

                except TimeoutException:
                    terminal_print(f"[ERREUR] Délai dépassé pour {media_id}")
                    errors += 1

                except NoSuchElementException:
                    terminal_print(f"[ERREUR] Menu introuvable pour {media_id}")
                    errors += 1

                except Exception as e:
                    terminal_print(f"[ERREUR] {media_id} : {e}")
                    errors += 1

                if errors >= max_errors:
                    terminal_print("Arrêt de sécurité : trop d'erreurs consécutives.")
                    break

            terminal_print("")
            terminal_print("==============================")
            terminal_print("NETTOYAGE TERMINÉ")
            terminal_print(f"Médias placés dans la corbeille : {deleted}")
            terminal_print(f"Erreurs : {errors}")
            terminal_print("==============================")
            terminal_print("Les médias restent récupérables dans la corbeille.")

        except Exception as e:
            terminal_print(f"Erreur delflow : {type(e).__name__}: {e}")

        # Ne pas fermer Chrome : session existante.

    threading.Thread(target=worker, daemon=True).start()


# ============================================================
# gen_video : indépendante de la langue du compte Flow
# ============================================================

FLOW_PROMPT_CSS = (
    "flow-rich-text-editor.prompt-input "
    "[role='textbox'][contenteditable='true']"
)


def _flow_find_first(driver, locators, timeout=20, must_be_enabled=False):
    """Retourne le premier élément visible parmi plusieurs localisateurs."""
    from selenium.common.exceptions import StaleElementReferenceException

    end = time.time() + timeout
    while time.time() < end:
        for by, sel in locators:
            try:
                for el in driver.find_elements(by, sel):
                    if el.is_displayed() and (not must_be_enabled or el.is_enabled()):
                        return el
            except StaleElementReferenceException:
                continue
        time.sleep(0.4)
    return None


# Attente de fin de génération vidéo (en secondes)
GEN_VIDEO_MIN_WAIT = 60      # jamais conclure « terminé » avant ce délai
GEN_VIDEO_TIMEOUT = 900      # abandon de l'attente après ce délai

_FLOW_READY_VIDEOS_JS = """
const ready = [];
let busyCount = 0, total = 0;
document.querySelectorAll('flow-grid-tile-container').forEach(c => {
    const vt = c.querySelector('flow-video-tile');
    if (!vt) return;
    total++;
    // Occupée = vrai spinner de chargement, ou une ligne qui n'est QUE « 45 % ».
    // (l'ancienne version prenait aussi toute barre de progression et tout
    // « n % » dans le texte, ce qui bloquait sur des tuiles déjà terminées)
    const lines = (c.innerText || '').split(/\\n/).map(x => x.trim());
    const busy = !!c.querySelector('mat-progress-spinner, mat-spinner')
              || lines.some(x => /^\\d{1,3}\\s*%$/.test(x));
    if (busy) { busyCount++; return; }
    const th = vt.querySelector('img.thumbnail');
    const thumb = th ? (th.currentSrc || th.src || '') : '';
    if (thumb && !thumb.startsWith('data:')) ready.push(thumb);
});
return {ready: ready, busy: busyCount, total: total};
"""


def _flow_video_state(driver):
    """Etat de la galerie : miniatures prêtes, tuiles occupées, nombre total de vidéos."""
    try:
        driver.execute_script(_FLOW_SCROLLER_JS + """
            const s = scroller(); if (s) s.scrollTop = 0;
        """)
        time.sleep(1)
        st = driver.execute_script(_FLOW_READY_VIDEOS_JS) or {}
        return {"ready": list(st.get("ready", [])),
                "busy": int(st.get("busy", 0)),
                "total": int(st.get("total", 0))}
    except Exception:
        return {"ready": [], "busy": 0, "total": 0}


def _flow_ready_video_keys(driver):
    """Miniatures des vidéos prêtes (haut de la galerie, où arrivent les nouvelles)."""
    return set(_flow_video_state(driver)["ready"])


def _flow_wait_new_video(driver, before, log):
    """Attend qu'une nouvelle vidéo apparaisse dans la galerie, terminée.

    `before` = état de la galerie juste avant le lancement (_flow_video_state).
    Deux façons de conclure :
      1) une miniature prête qui n'existait pas avant ;
      2) secours : plus aucune tuile occupée ET une vidéo de plus qu'avant,
         stable sur 3 contrôles et après au moins 120 s.
    """
    if not isinstance(before, dict):  # ancien format : simple ensemble de miniatures
        before = {"ready": list(before), "total": 0}
    before_ready = set(before.get("ready", []))
    before_total = before.get("total", 0)

    start = time.time()
    stable = 0
    stable_fallback = 0
    dumped = False
    log("Attente de la fin de la génération vidéo...", "#ffaa00")
    last_report = 0

    while time.time() - start < GEN_VIDEO_TIMEOUT:
        time.sleep(5)
        elapsed = time.time() - start
        st = _flow_video_state(driver)

        new_ready = set(st["ready"]) - before_ready
        if new_ready and elapsed >= GEN_VIDEO_MIN_WAIT:
            stable += 1
            if stable >= 2:  # présente et inchangée sur 2 contrôles
                log(f"Vidéo prête ({int(elapsed)} s).", "#55ff55")
                return True
        else:
            stable = 0

        grew = st["total"] > before_total and st["busy"] == 0
        if grew and elapsed >= 120:
            stable_fallback += 1
            if stable_fallback >= 3:
                log(f"Vidéo prête ({int(elapsed)} s, détection de secours).", "#55ff55")
                return True
        else:
            stable_fallback = 0

        # Une seule fois, on garde la page pour comprendre si ça bloque
        if not dumped and elapsed >= 180:
            dumped = True
            _flow_dump(driver, "video_wait_180s", log)

        if elapsed - last_report >= 30:
            last_report = elapsed
            log(f"... génération en cours ({int(elapsed)} s) "
                f"[prêtes : {len(st['ready'])}, occupées : {st['busy']}, "
                f"total : {st['total']}]", "#888888")

    log(f"Délai dépassé ({GEN_VIDEO_TIMEOUT} s) : vidéo non détectée, on continue.",
        "#ffaa00")
    _flow_dump(driver, "video_wait_timeout", log)
    return False


def cmd_gen_video(args):

    if len(args) != 3:
        terminal_print('Usage : gen_video <profil> "<image>" "<prompt>"', "#ff5555")
        return

    profile_name = args[0].strip('"')
    image_path = Path(args[1].strip('"'))
    prompt = args[2]

    if not image_path.is_file():
        terminal_print(f"Image introuvable : {image_path}", "#ff5555")
        return

    def worker():
        def log(message, color="#ffffff"):
            root.after(0, lambda m=message, c=color: terminal_print(m, c))

        driver = None
        step = "init"

        try:
            # ---------- 1. Projet Flow + Chrome ----------
            project_url = get_flow_project_url(profile_name)
            if not project_url:
                log(
                    f"Aucun projet Flow enregistré pour {profile_name}. "
                    f"Lance cresce {profile_name}, ouvre ton projet puis "
                    f"tape cproject {profile_name}.",
                    "#ff5555"
                )
                return

            log(f"Vérification du profil : {profile_name}", "#55aaff")

            driver = connect_selenium(profile_name, project_url, log)
            if driver is None:
                return

            wait = WebDriverWait(driver, 30)
            log("Connexion Chrome OK.", "#55ff55")

            # ---------- 2. Se placer sur l'onglet du projet ----------
            step = "projet"
            if not ensure_flow_project_tab(driver, profile_name, log):
                return

            step = "champ prompt"
            editor = _flow_find_first(
                driver, [(By.CSS_SELECTOR, FLOW_PROMPT_CSS)], timeout=45
            )
            if editor is None:
                log(f"Champ de prompt introuvable. URL : {driver.current_url}", "#ff5555")
                log(
                    "Vérifie que le compte est connecté à Google et qu'aucune "
                    "fenêtre (conditions, bienvenue...) ne bloque Flow.",
                    "#ffaa00"
                )
                _flow_dump(driver, "video_prompt", log)
                return

            log("Google Flow détecté.", "#55ff55")

            # ---------- 3. Forcer le mode VIDÉO ----------
            step = "réglages"
            log("Configuration du mode vidéo...", "#55aaff")

            configure_flow_settings(
                driver, log, "videocam", "x1",
                type_icon="chrome_extension", model_keyword="veo 3.1"
            )

            # ---------- 4. Panneau « ingrédients » (bouton +) ----------
            step = "bouton ingrédients"
            add_btn = _flow_find_first(
                driver,
                [
                    (By.CSS_SELECTOR, "flow-add-menu button.add-menu-trigger"),
                    (By.CSS_SELECTOR, "button.add-menu-trigger"),
                    (By.XPATH, '//button[.//mat-icon[normalize-space()="add"]]'),
                ],
                timeout=20, must_be_enabled=True
            )
            if add_btn is None:
                log("Bouton + (ingrédients) introuvable.", "#ff5555")
                _flow_dump(driver, "video_addmenu", log)
                return

            driver.execute_script("arguments[0].click();", add_btn)
            time.sleep(1)

            # ---------- 5. Import de l'image ----------
            step = "import image"

            # Intercepte l'ouverture du sélecteur de fichiers Windows
            driver.execute_script("""
                window.__flowFileInput = null;
                if (!HTMLInputElement.prototype.__origClick) {
                    HTMLInputElement.prototype.__origClick =
                        HTMLInputElement.prototype.click;
                }
                HTMLInputElement.prototype.click = function() {
                    if (this.type === 'file') {
                        window.__flowFileInput = this;
                        return;
                    }
                    return HTMLInputElement.prototype.__origClick.call(this);
                };
            """)

            upload_btn = _flow_find_first(
                driver,
                [
                    (By.CSS_SELECTOR, "button.sidebar-upload-btn"),
                    (By.XPATH,
                     '//button[.//mat-icon[normalize-space()="upload" '
                     'or normalize-space()="upload_file" '
                     'or normalize-space()="add_photo_alternate"]]'),
                ],
                timeout=20, must_be_enabled=True
            )
            if upload_btn is None:
                log("Bouton d'import introuvable.", "#ff5555")
                _flow_dump(driver, "video_upload", log)
                return

            driver.execute_script("arguments[0].click();", upload_btn)

            file_input = None
            end = time.time() + 10
            while time.time() < end and file_input is None:
                file_input = driver.execute_script("return window.__flowFileInput;")
                if file_input is None:
                    time.sleep(0.3)

            # Secours : un <input type=file> déjà présent dans la page
            if file_input is None:
                inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                if inputs:
                    file_input = inputs[-1]

            if file_input is None:
                log("Champ fichier introuvable.", "#ff5555")
                _flow_dump(driver, "video_fileinput", log)
                return

            file_input.send_keys(str(image_path.resolve()))
            log("Image envoyée à Google Flow.", "#55aaff")

            # ---------- 6. Ajouter l'image au prompt ----------
            step = "ajout au prompt"
            log("Ajout de l'image au prompt (attente de l'upload)...", "#55aaff")

            add_to_prompt = _flow_find_first(
                driver,
                [(By.CSS_SELECTOR, "button.detail-add-to-prompt-btn")],
                timeout=90, must_be_enabled=True
            )
            if add_to_prompt is None:
                log("Bouton « ajouter au prompt » introuvable.", "#ff5555")
                _flow_dump(driver, "video_addtoprompt", log)
                return

            time.sleep(1)
            driver.execute_script("arguments[0].click();", add_to_prompt)
            log("Image ajoutée au prompt.", "#55ff55")

            try:
                WebDriverWait(driver, 15).until(
                    EC.invisibility_of_element_located(
                        (By.CSS_SELECTOR, ".cdk-overlay-backdrop")
                    )
                )
            except Exception:
                pass

            time.sleep(1)

            # ---------- 7. Saisie du prompt ----------
            step = "saisie prompt"
            editor = _flow_find_first(
                driver, [(By.CSS_SELECTOR, FLOW_PROMPT_CSS)], timeout=20
            )
            if editor is None:
                log("Champ de prompt perdu après l'ajout de l'image.", "#ff5555")
                _flow_dump(driver, "video_prompt2", log)
                return

            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", editor
            )
            driver.execute_script("arguments[0].focus();", editor)
            editor.send_keys(prompt)
            time.sleep(0.8)

            typed = editor.get_attribute("innerText") or editor.text or ""
            if prompt.strip() not in typed:
                log("Le prompt n'est pas confirmé dans le champ.", "#ff5555")
                return

            log("Prompt inséré et vérifié.", "#55ff55")

            # ---------- 8. Génération ----------
            step = "génération"
            generate_button = _flow_find_first(
                driver,
                [
                    (By.CSS_SELECTOR, "button.generate-icon-button"),
                    (By.CSS_SELECTOR, "flow-generate-icon-button button"),
                ],
                timeout=20
            )
            if generate_button is None:
                log("Bouton de génération introuvable.", "#ff5555")
                _flow_dump(driver, "video_generate", log)
                return

            end = time.time() + 30
            while time.time() < end and not generate_button.is_enabled():
                time.sleep(0.5)

            if not generate_button.is_enabled():
                log(
                    "Le bouton de génération reste désactivé "
                    "(crédits insuffisants ou image non prise en compte ?).",
                    "#ff5555"
                )
                _flow_dump(driver, "video_generate", log)
                return

            # Vidéos déjà prêtes avant la génération (pour repérer la nouvelle)
            step = "attente génération"
            before_keys = _flow_video_state(driver)

            log("Lancement de Veo 3.1...", "#55aaff")
            driver.execute_script("arguments[0].click();", generate_button)
            log("Génération lancée ! Format vertical 9:16, 1 vidéo.", "#55ff55")

            # La commande ne se termine qu'une fois la vidéo prête : c'est ce qui
            # fait attendre la ligne suivante d'un script CD (save, delflow...).
            _flow_wait_new_video(driver, before_keys, log)

        except Exception as e:
            log(
                f"Erreur gen_video (étape « {step} ») : {type(e).__name__}: {e}",
                "#ff5555"
            )
            if driver is not None:
                _flow_dump(driver, "video_error", log)

        finally:
            log("Commande gen_video terminée.", "#aaaaaa")

    threading.Thread(target=worker, daemon=True).start()


# ============================================================
# montage : éditeur vidéo graphique (sélection à la souris, coupes franches, avec le son)
# ============================================================
# Utilisation :
#   montage                         -> clips du dossier "video", sortie montage.mp4
#   montage dossier                 -> clips d'un autre dossier
#   montage dossier final.mp4       -> nom du fichier final
#
# La fenêtre ouvre les vidéos UNE PAR UNE (1.mp4, 2.mp4, ...). Sous l'image, une
# frise montre toute la vidéo ; la partie gardée est encadrée en vert.
#
#   Souris  : clic / glisser sur la frise = se déplacer dans la vidéo
#             glisser une poignée verte    = déplacer le début ou la fin
#             Maj + glisser                = sélectionner une zone (en bleu)
#   Clavier : Espace = lecture/pause (saute les parties supprimées)
#             ← → = image par image (Maj = 1 s)
#             I / O = début / fin ici (coupe les blancs avant / après la tête de lecture)
#             C = couper en deux à la tête de lecture
#             Suppr = supprimer la zone bleue (ou le morceau cliqué)
#             R = tout remettre     Entrée = valider et passer à la suivante
#
# Après la dernière vidéo, Entrée lance l'assemblage : les morceaux gardés sont collés
# bout à bout, sans transition, avec leur son, accélérés de MONTAGE_SPEED, avec une
# musique de fond par-dessus (réglages ci-dessous). Les découpes sont mémorisées dans
# <dossier>/_montage.json. Nécessite FFmpeg (ffmpeg et ffprobe dans le PATH).

import tempfile
import ctypes

# ---- Réglages de la vidéo finale (modifiables) ----
MONTAGE_SPEED = 1.3             # vitesse de toute la vidéo (1.0 = normale, 1.3 = 30 % plus vite)
MONTAGE_MUSIC = "son.mp3"       # musique de fond ; None = aucune. Cherchée dans le dossier
                                # courant puis à côté de main.py (ou mets un chemin complet)
MONTAGE_MUSIC_VOLUME = 0.15     # volume de la musique : 0.15 = 15 % (1.0 = volume d'origine)
MONTAGE_VOICE_VOLUME = 1.5      # volume du son des vidéos (la voix) : 1.5 = 150 %

# Son synchronisé : sous Windows, le son est joué par MCI (winmm, déjà dans Windows,
# rien à installer) et c'est LUI qui sert d'horloge à l'image. Image et son ne peuvent
# donc plus se décaler. Ailleurs : lecture par ffplay, image sur l'horloge système.
_MCI_OK = platform.system() == "Windows" and hasattr(ctypes, "windll")
_MCI_ALIAS = "montage_snd"
MONTAGE_AUDIO_OFFSET = 0.0   # secondes ; si l'image est en retard sur le son, mets une valeur
                             # négative (ex : -0.08), si elle est en avance, positive.


def _mci(command):
    """Envoie une commande MCI. Renvoie (code d'erreur, texte de réponse)."""
    buf = ctypes.create_unicode_buffer(256)
    err = ctypes.windll.winmm.mciSendStringW(command, buf, 255, 0)
    return err, buf.value

MONTAGE_FPS = 30                   # images/s de la vidéo finale
MONTAGE_PREVIEW_FPS = 15           # images/s de l'aperçu dans l'éditeur
MONTAGE_MIN_SEGMENT = 0.1          # durée minimale d'un morceau gardé (s)
_MONTAGE_EXTS = {".mp4", ".mov", ".webm", ".mkv"}


def _no_window():
    """Évite l'ouverture d'une console noire à chaque appel FFmpeg sous Windows."""
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def _run_capture(cmd):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **_no_window())


def _probe_clip(path):
    """Renvoie (durée en secondes, a une piste audio, (largeur, hauteur))."""
    def probe(*a):
        return _run_capture(["ffprobe", "-v", "error", *a, str(path)]).stdout.strip()

    duration = float(probe("-show_entries", "format=duration", "-of", "csv=p=0"))
    has_audio = bool(probe("-select_streams", "a",
                           "-show_entries", "stream=index", "-of", "csv=p=0"))
    dims = probe("-select_streams", "v:0",
                 "-show_entries", "stream=width,height", "-of", "csv=p=0")
    width, height = (int(x) for x in dims.split(",")[:2])
    return duration, has_audio, (width, height)


# ---------- découpe en morceaux gardés : [(début, fin), ...] triés ----------

def _seg_split(segments, t):
    out = []
    for s, e in segments:
        if s + MONTAGE_MIN_SEGMENT < t < e - MONTAGE_MIN_SEGMENT:
            out += [(s, t), (t, e)]
        else:
            out.append((s, e))
    return out


def _seg_subtract(segments, a, b):
    """Retire la zone [a, b] des morceaux gardés."""
    out = []
    for s, e in segments:
        if b <= s or a >= e:
            out.append((s, e))
            continue
        if a - s >= MONTAGE_MIN_SEGMENT:
            out.append((s, a))
        if e - b >= MONTAGE_MIN_SEGMENT:
            out.append((b, e))
    return out


# ---------- assemblage FFmpeg ----------

def _find_music():
    """Chemin de la musique de fond, ou None si désactivée / introuvable."""
    if not MONTAGE_MUSIC:
        return None
    path = Path(MONTAGE_MUSIC)
    candidates = [path] if path.is_absolute() else [
        Path.cwd() / path, Path(__file__).resolve().parent / path]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _atempo_chain(speed):
    """Filtre FFmpeg de vitesse du son (atempo accepte 0,5 à 2 par étage)."""
    parts = []
    while speed > 2.0:
        parts.append("atempo=2.0")
        speed /= 2.0
    while speed < 0.5:
        parts.append("atempo=0.5")
        speed /= 0.5
    parts.append(f"atempo={speed:.4f}")
    return ",".join(parts)


def _montage_command(clips, out_path):
    """Commande FFmpeg : découpe de chaque morceau, collage bout à bout (coupes franches),
    accélération de toute la vidéo, puis musique de fond mélangée par-dessus.

    clips : dicts avec path, start, end, has_audio, size
    """
    width, height = clips[0]["size"]
    inputs, parts = [], []
    music = _find_music()

    for i, c in enumerate(clips):
        inputs += ["-i", str(c["path"])]
        s, e = c["start"], c["end"]
        parts.append(
            f"[{i}:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS,"
            f"fps={MONTAGE_FPS},scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[v{i}]"
        )
        if c["has_audio"]:
            parts.append(
                f"[{i}:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS,"
                f"aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]"
            )
        else:  # clip sans son : silence de la même durée
            parts.append(
                f"anullsrc=r=48000:cl=stereo,atrim=duration={e - s:.3f},"
                f"asetpts=PTS-STARTPTS[a{i}]"
            )
    joined = "".join(f"[v{i}][a{i}]" for i in range(len(clips)))
    parts.append(f"{joined}concat=n={len(clips)}:v=1:a=1[cv][ca]")

    # vitesse de toute la vidéo (image + son, la voix garde sa hauteur)
    parts.append(f"[cv]setpts=PTS/{MONTAGE_SPEED},fps={MONTAGE_FPS}[outv]")
    parts.append(f"[ca]{_atempo_chain(MONTAGE_SPEED)},volume={MONTAGE_VOICE_VOLUME}[sa]")

    if music is not None:
        # La musique démarre avec la vidéo, n'est ni accélérée ni bouclée : si elle est plus
        # courte, silence après sa fin ; si elle est plus longue, elle s'arrête avec la vidéo.
        # (apad la prolonge de silence pour que le volume de la voix ne bouge pas à la fin
        # de la musique ; amix divise par 2 les entrées, volume=2 compense ; le limiteur
        # évite seulement la saturation, sans modifier le niveau.)
        inputs += ["-i", str(music)]
        m = len(clips)
        parts.append(
            f"[{m}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"volume={MONTAGE_MUSIC_VOLUME},apad[mus]"
        )
        parts.append(
            "[sa][mus]amix=inputs=2:duration=first:dropout_transition=0,"
            "volume=2,alimiter=limit=0.95:level=0[outa]"
        )
    else:
        parts.append("[sa]alimiter=limit=0.95:level=0[outa]")
    graph = ";".join(parts)

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs]
    if len(graph) > 20000:   # évite la limite de longueur de ligne de commande (Windows)
        script = Path(tempfile.gettempdir()) / "montage_filter.txt"
        script.write_text(graph, encoding="utf-8")
        cmd += ["-filter_complex_script", str(script)]
    else:
        cmd += ["-filter_complex", graph]
    cmd += [
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        str(out_path),
    ]
    return cmd


def _run_montage(clips, out_path, log):
    """Lance FFmpeg et indique le résultat."""
    started = time.time()
    if MONTAGE_MUSIC and _find_music() is None:
        log(f"Musique « {MONTAGE_MUSIC} » introuvable (dossier courant ou à côté de "
            f"main.py) : montage sans musique.", "#ffaa00")
    proc = _run_capture(_montage_command(clips, out_path))
    if proc.returncode == 0:
        total = sum(c["end"] - c["start"] for c in clips) / MONTAGE_SPEED
        music = "avec musique" if _find_music() else "sans musique"
        log(f"Montage terminé en {int(time.time() - started)} s "
            f"({len(clips)} morceau(x), {total:.1f} s à x{MONTAGE_SPEED:g}, {music}) "
            f": {out_path}", "#55ff55")
        return True
    tail = "\n".join(proc.stderr.strip().splitlines()[-6:])
    log(f"Échec FFmpeg :\n{tail}", "#ff5555")
    return False


# ---------- éditeur graphique ----------

class MontageEditor:
    BG, FG, FIELD = "#1e1e1e", "#ffffff", "#2d2d2d"
    ACCENT, ORANGE, RED, BLUE = "#00ff88", "#ffaa00", "#ff4444", "#3399ff"
    TL_PAD = 14          # marge gauche/droite de la frise
    HANDLE_GRAB = 9      # distance (px) pour attraper une poignée

    def __init__(self, folder, out_path, clips):
        self.folder, self.out_path, self.clips = folder, out_path, clips
        self.tmp = Path(tempfile.mkdtemp(prefix="montage_"))
        self.settings_path = folder / "_montage.json"
        try:
            self.saved = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except Exception:
            self.saved = {}

        self.segments = {}          # index du clip -> [[début, fin], ...]
        self.frames_count = {}      # index du clip -> nombre d'images d'aperçu
        self.extracting = set()
        self.index = 0
        self.t = 0.0
        self.sel_seg = None
        self.sel_range = None
        self.drag = None
        self.playing = False
        self.audio = None           # processus ffplay (hors Windows)
        self.mci_open = False       # fichier audio ouvert dans MCI
        self.mci_playing = False    # le son est en cours de lecture
        self.closed = False
        self.busy = False
        self._shown = None
        self._thumbs = {}
        self.photo = None

        self._build_ui()
        self.show_clip(0)

    # ----- construction de la fenêtre -----
    def _build_ui(self):
        BG, FG, FIELD = self.BG, self.FG, self.FIELD
        w = self.win = tk.Toplevel(root)
        w.title("Montage vidéo")
        w.configure(bg=BG)
        w.geometry("900x780")
        w.minsize(700, 620)

        self.title_var = tk.StringVar()
        self.info_var = tk.StringVar()
        tk.Label(w, textvariable=self.title_var, bg=BG, fg=FG,
                 font=("Segoe UI", 13, "bold")).pack(pady=(10, 0))
        tk.Label(w, textvariable=self.info_var, bg=BG, fg="#aaaaaa").pack()

        holder = tk.Frame(w, bg="#000000", height=self.clips[0]["disp_max_h"])
        holder.pack(fill="x", padx=14, pady=8)
        holder.pack_propagate(False)
        self.video_label = tk.Label(holder, bg="#000000", fg="#888888",
                                    text="Chargement de l'aperçu...")
        self.video_label.pack(expand=True)

        self.thumb_h = max(c["thumb_h"] for c in self.clips)
        self.canvas = tk.Canvas(w, height=self.thumb_h + 52, bg="#111111",
                                highlightthickness=0)
        self.canvas.pack(fill="x", padx=14)
        self.canvas.bind("<Button-1>", lambda e: self.on_press(e, bool(e.state & 1)))
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Configure>", lambda e: self.redraw())

        self.time_var = tk.StringVar()
        tk.Label(w, textvariable=self.time_var, bg=BG, fg=self.ORANGE,
                 font=("Consolas", 11)).pack(pady=(6, 0))

        bar = tk.Frame(w, bg=BG)
        bar.pack(pady=(8, 2))
        bar2 = tk.Frame(w, bg=BG)
        bar2.pack(pady=(2, 8))

        def button(parent, text, command, bg=FIELD, fg=FG):
            b = tk.Button(parent, text=text, command=command, bg=bg, fg=fg, relief="flat",
                          padx=10, pady=5, takefocus=0)
            b.pack(side="left", padx=3)
            return b

        button(bar, "▶ Lecture (Espace)", self.toggle_play)
        button(bar, "✂ Couper (C)", self.split)
        button(bar, "Début ici (I)", self.mark_in)
        button(bar, "Fin ici (O)", self.mark_out)
        button(bar, "🗑 Supprimer (Suppr)", self.delete)
        button(bar2, "◀ Précédente", self.previous)
        button(bar2, "↺ Tout remettre (R)", self.reset)
        self.next_btn = button(bar2, "Valider ▶ (Entrée)", self.next,
                               bg=self.ACCENT, fg="#000000")

        self.status = tk.StringVar(value="")
        tk.Label(w, textvariable=self.status, bg=BG, fg=self.ORANGE, wraplength=860,
                 justify="left").pack(fill="x", padx=14)
        tk.Label(w, text="Frise : clic = se déplacer · glisser une poignée verte = ajuster "
                         "· Maj + glisser = zone à supprimer",
                 bg=BG, fg="#777777").pack(pady=(2, 8))

        w.bind("<Key>", self.on_key)
        w.protocol("WM_DELETE_WINDOW", self.close)
        w.focus_force()

    # ----- images d'aperçu (extraites une fois par clip, en arrière-plan) -----
    def _ensure_frames(self, i):
        if i >= len(self.clips) or i in self.frames_count or i in self.extracting:
            return
        self.extracting.add(i)
        clip = self.clips[i]
        fw, fh = clip["disp"]
        out_dir = self.tmp / f"c{i}"

        def work():
            out_dir.mkdir(parents=True, exist_ok=True)
            if _MCI_OK and clip["has_audio"]:
                # piste audio complète en WAV : MCI la lit sans délai et donne sa position
                _run_capture([
                    "ffmpeg", "-y", "-loglevel", "error", "-i", str(clip["path"]),
                    "-vn", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le",
                    str(out_dir / "audio.wav"),
                ])
            _run_capture([
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(clip["path"]), "-an",
                "-vf", f"fps={MONTAGE_PREVIEW_FPS},scale={fw}:{fh}",
                "-compression_level", "1", str(out_dir / "%04d.png"),
            ])
            self.frames_count[i] = len(list(out_dir.glob("*.png")))
            self.extracting.discard(i)

        threading.Thread(target=work, daemon=True).start()

    def _wait_frames(self, i):
        if self.closed or i != self.index:
            return
        if i in self.frames_count:
            self._shown = None
            if self.frames_count[i] == 0:
                self.status.set("Aperçu indisponible pour cette vidéo (FFmpeg a échoué).")
            self._open_audio()
            self.show_frame()
            self.redraw()
            self._ensure_frames(i + 1)      # précharge la suivante
            return
        self.win.after(100, lambda: self._wait_frames(i))

    def show_frame(self):
        n = self.frames_count.get(self.index)
        if not n:
            return
        k = min(n, max(1, int(self.t * MONTAGE_PREVIEW_FPS) + 1))
        if k == self._shown:
            return
        try:
            img = tk.PhotoImage(file=str(self.tmp / f"c{self.index}" / f"{k:04d}.png"))
        except tk.TclError:
            return
        self.photo = img
        self.video_label.config(image=img, text="")
        self._shown = k

    def _thumb(self, k):
        if k not in self._thumbs:
            clip = self.clips[self.index]
            try:
                img = tk.PhotoImage(
                    file=str(self.tmp / f"c{self.index}" / f"{k:04d}.png")
                ).subsample(clip["thumb_factor"])
            except tk.TclError:
                img = None
            self._thumbs[k] = img
        return self._thumbs[k]

    # ----- navigation entre les clips -----
    def show_clip(self, i):
        self.pause()
        self._close_audio()
        self.index = i
        clip = self.clips[i]
        self.t = 0.0
        self.sel_seg = self.sel_range = None
        self._shown = None
        self._thumbs = {}
        self.photo = None
        self.video_label.config(image="", text="Chargement de l'aperçu...")

        if i not in self.segments:
            saved = self.saved.get(clip["path"].name, {}).get("segments")
            if saved is not None:
                segs = [[max(0.0, float(s)), min(clip["duration"], float(e))]
                        for s, e in saved]
            else:
                segs = [[0.0, clip["duration"]]]
            self.segments[i] = segs

        self.title_var.set(f"Vidéo {i + 1} / {len(self.clips)} — {clip['path'].name}")
        self.info_var.set(f"Durée : {clip['duration']:.2f} s")
        self.next_btn.config(text="Assembler ▶ (Entrée)" if i == len(self.clips) - 1
                             else "Valider ▶ (Entrée)")
        self.status.set("")
        self._ensure_frames(i)
        self._wait_frames(i)
        self.redraw()

    def _store(self):
        """Mémorise les découpes du clip courant (mémoire + fichier)."""
        self.segments[self.index] = [list(s) for s in self.segments[self.index]]
        data = {}
        for i, segs in self.segments.items():
            data[self.clips[i]["path"].name] = {
                "segments": [[round(s, 3), round(e, 3)] for s, e in segs]}
        self.saved.update(data)
        try:
            self.settings_path.write_text(
                json.dumps(self.saved, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def previous(self):
        if self.busy or self.index == 0:
            return
        self._store()
        self.show_clip(self.index - 1)

    def next(self):
        if self.busy:
            return
        self.pause()
        self._store()
        if self.index + 1 < len(self.clips):
            self.show_clip(self.index + 1)
        else:
            self.finish()

    def finish(self):
        flat = []
        for i, clip in enumerate(self.clips):
            for s, e in self.segments.get(i, []):
                flat.append({**clip, "start": s, "end": e})
        if not flat:
            self.status.set("Aucun morceau gardé : rien à assembler.")
            return
        self.busy = True
        self.next_btn.config(state="disabled", text="Assemblage...")
        self.status.set("Assemblage en cours, patiente (détails dans le terminal)...")
        log = self.log
        log(f"Montage de {len(flat)} morceau(x) -> {self.out_path}", "#ffaa00")

        def work():
            try:
                ok = _run_montage(flat, self.out_path, log)
            except Exception as exc:
                log(f"Erreur montage : {type(exc).__name__}: {exc}", "#ff5555")
                ok = False

            def done():
                if self.closed:
                    return
                if ok:
                    self.close()
                else:
                    self.busy = False
                    self.next_btn.config(state="normal", text="Assembler ▶ (Entrée)")
                    self.status.set("Échec de l'assemblage, voir le terminal.")
            try:
                root.after(0, done)
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def log(self, message, color=None):
        try:
            root.after(0, lambda m=message, c=color: terminal_print(m, c))
        except Exception:
            print(message)

    def close(self):
        if self.closed:
            return
        try:
            self._store()
        except Exception:
            pass
        self.closed = True
        self.pause()
        self._close_audio()
        try:
            self.win.destroy()
        except tk.TclError:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ----- géométrie de la frise -----
    @property
    def segs(self):
        return self.segments[self.index]

    @property
    def dur(self):
        return self.clips[self.index]["duration"]

    def _tl_x(self):
        width = max(self.canvas.winfo_width(), 200)
        return self.TL_PAD, width - self.TL_PAD

    def t2x(self, t):
        x0, x1 = self._tl_x()
        return x0 + (t / self.dur) * (x1 - x0)

    def x2t(self, x):
        x0, x1 = self._tl_x()
        return min(self.dur, max(0.0, (x - x0) / (x1 - x0) * self.dur))

    def _segment_at(self, t):
        for k, (s, e) in enumerate(self.segs):
            if s <= t < e:
                return k
        return None

    # ----- dessin -----
    def redraw(self):
        if self.closed:
            return
        c = self.canvas
        c.delete("all")
        x0, x1 = self._tl_x()
        top = 18
        clip = self.clips[self.index]
        bot = top + clip["thumb_h"]
        dur = self.dur

        n = self.frames_count.get(self.index, 0)
        if n:
            tw = max(1, clip["disp"][0] // clip["thumb_factor"])
            count = max(1, round((x1 - x0) / tw))
            for k in range(count):
                frame = min(n, max(1, int((k + 0.5) / count * dur * MONTAGE_PREVIEW_FPS) + 1))
                img = self._thumb(frame)
                if img is not None:
                    c.create_image(x0 + k * (x1 - x0) / count, top, image=img, anchor="nw")
        else:
            c.create_rectangle(x0, top, x1, bot, fill="#222222", outline="")

        # parties supprimées (assombries)
        prev = 0.0
        for s, e in list(self.segs) + [(dur, dur)]:
            if s > prev:
                c.create_rectangle(self.t2x(prev), top, self.t2x(s), bot,
                                   fill="#000000", stipple="gray75", outline="")
            prev = e

        # morceaux gardés + poignées
        for k, (s, e) in enumerate(self.segs):
            color = self.ORANGE if k == self.sel_seg else self.ACCENT
            c.create_rectangle(self.t2x(s), top, self.t2x(e), bot, outline=color, width=2)
            for t in (s, e):
                x = self.t2x(t)
                c.create_rectangle(x - 3, top - 4, x + 3, bot + 4, fill=color, outline="")

        # zone sélectionnée à la souris (Maj + glisser)
        if self.sel_range:
            a, b = self.sel_range
            c.create_rectangle(self.t2x(a), top, self.t2x(b), bot, fill=self.BLUE,
                               stipple="gray50", outline=self.BLUE, width=2)

        # règle graduée
        step = 1 if dur <= 20 else 5
        t = 0
        while t <= dur:
            x = self.t2x(t)
            c.create_line(x, bot + 6, x, bot + 12, fill="#888888")
            c.create_text(x, bot + 24, text=f"{t:g}s", fill="#888888", font=("Segoe UI", 8))
            t += step

        self._draw_playhead()

    def _draw_playhead(self):
        c = self.canvas
        c.delete("ph")
        x = self.t2x(self.t)
        bot = 18 + self.clips[self.index]["thumb_h"]
        c.create_line(x, 6, x, bot + 8, fill=self.RED, width=2, tags="ph")
        c.create_polygon(x - 6, 0, x + 6, 0, x, 10, fill=self.RED, outline="", tags="ph")
        kept = sum(e - s for s, e in self.segs)
        self.time_var.set(f"{self.t:6.2f} s / {self.dur:.2f} s    |    "
                          f"gardé : {kept:.2f} s ({len(self.segs)} morceau(x))")

    # ----- souris -----
    def _hit_handle(self, x):
        best, best_score = None, None
        for k, (s, e) in enumerate(self.segs):
            for which, t in (("s", s), ("e", e)):
                px = self.t2x(t)
                d = abs(px - x)
                if d > self.HANDLE_GRAB:
                    continue
                # poignées superposées (morceaux collés) : celle du côté de la souris
                score = d + (0 if (which == "e") == (x <= px) else 0.5)
                if best_score is None or score < best_score:
                    best, best_score = (k, which), score
        return best

    def on_press(self, event, shift):
        self.win.focus_set()
        self.pause()
        t = self.x2t(event.x)
        if shift:
            self.drag = ("range", t)
            self.sel_range = (t, t)
            self.redraw()
            return
        handle = self._hit_handle(event.x)
        if handle:
            self.drag = ("handle", *handle)
            return
        self.drag = ("scrub",)
        self.sel_range = None
        self.sel_seg = self._segment_at(t)
        self.seek(t)
        self.redraw()

    def on_motion(self, event):
        if not self.drag:
            return
        t = self.x2t(event.x)
        kind = self.drag[0]
        if kind == "range":
            a = self.drag[1]
            self.sel_range = (min(a, t), max(a, t))
            self.redraw()
        elif kind == "scrub":
            self.seek(t)
        elif kind == "handle":
            k, which = self.drag[1], self.drag[2]
            segs = self.segs
            if which == "s":
                lo = segs[k - 1][1] if k > 0 else 0.0
                hi = segs[k][1] - MONTAGE_MIN_SEGMENT
                segs[k][0] = min(hi, max(lo, t))
                self.t = segs[k][0]
            else:
                lo = segs[k][0] + MONTAGE_MIN_SEGMENT
                hi = segs[k + 1][0] if k + 1 < len(segs) else self.dur
                segs[k][1] = min(hi, max(lo, t))
                self.t = segs[k][1]
            self.show_frame()
            self.redraw()

    def on_release(self, event):
        if self.drag and self.drag[0] == "range":
            a, b = self.sel_range
            if b - a < 0.05:
                self.sel_range = None
        self.drag = None
        self.redraw()

    # ----- lecture -----
    def seek(self, t):
        self.t = min(self.dur, max(0.0, t))
        self.show_frame()
        self._draw_playhead()

    def _next_valid(self, t):
        for s, e in self.segs:
            if s <= t < e:
                return t
            if s > t:
                return s
        return None

    def _open_audio(self):
        """Ouvre le WAV du clip courant dans MCI (Windows)."""
        self._close_audio()
        if not _MCI_OK:
            return
        wav = self.tmp / f"c{self.index}" / "audio.wav"
        if not wav.exists():                     # clip sans son
            return
        err, _ = _mci(f'open "{wav}" type waveaudio alias {_MCI_ALIAS}')
        if err == 0:
            _mci(f"set {_MCI_ALIAS} time format milliseconds")
            self.mci_open = True

    def _close_audio(self):
        if self.mci_open:
            _mci(f"stop {_MCI_ALIAS}")
            _mci(f"close {_MCI_ALIAS}")
        self.mci_open = False
        self.mci_playing = False

    def _start_audio(self, t):
        """Lance le son de t jusqu'à la fin du morceau gardé qui contient t."""
        self._stop_audio()
        k = self._segment_at(t)
        if k is None:
            return
        end = self.segs[k][1]

        if self.mci_open:
            if int(end * 1000) <= int(t * 1000):
                return
            err, _ = _mci(f"play {_MCI_ALIAS} from {int(t * 1000)} to {int(end * 1000)}")
            if err == 0:
                self.mci_playing = True
                self._audio_end = end
                self._audio_from = t
                self._est = t                      # position estimée du son
                self._last_wall = self._audio_started = time.time()
            return

        if _MCI_OK or not shutil.which("ffplay"):
            return
        try:
            self.audio = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                 "-ss", f"{t:.3f}", "-t", f"{end - t:.3f}",
                 str(self.clips[self.index]["path"])],
                stdin=subprocess.DEVNULL, **_no_window())
        except OSError:
            self.audio = None

    def _stop_audio(self):
        if self.mci_playing:
            _mci(f"stop {_MCI_ALIAS}")
        self.mci_playing = False
        if self.audio is not None:
            try:
                self.audio.terminate()
                self.audio.wait(timeout=1)
            except Exception:
                try:
                    self.audio.kill()
                except Exception:
                    pass
            self.audio = None

    def toggle_play(self):
        if self.playing:
            self.pause()
            return
        if self.index not in self.frames_count:
            self.status.set("Chargement de l'aperçu, patiente une seconde...")
            return
        if not self.segs:
            self.status.set("Rien à lire : aucun morceau gardé.")
            return
        self.status.set("")
        start = self._next_valid(self.t)
        if start is None:                      # fin atteinte : on repart du début
            start = self.segs[0][0]
        self.t = start
        self._start_audio(start)
        self.playing = True
        self._play_wall, self._play_media = time.time(), start
        self._tick()

    def pause(self):
        self.playing = False
        self._stop_audio()

    def _audio_time(self, now):
        """Temps de lecture déduit de la position RÉELLE du son (None = son terminé)."""
        err, mode = _mci(f"status {_MCI_ALIAS} mode")
        if err != 0 or mode != "playing":
            # fini (ou pas encore démarré : on laisse 0,2 s de grâce)
            if now - self._audio_started > 0.2:
                self.mci_playing = False
                return None
            return self._est
        _, pos = _mci(f"status {_MCI_ALIAS} position")
        try:
            p = int(pos) / 1000.0 + MONTAGE_AUDIO_OFFSET
        except ValueError:
            p = None
        # le son n'a pas encore commencé à avancer : l'image attend (1 s maximum)
        if p is not None and p - self._audio_from < 0.001 and now - self._audio_started < 1.0:
            self._est, self._last_wall = self._audio_from, now
            return self._audio_from
        est = self._est + (now - self._last_wall)      # avance fluide entre deux lectures
        if p is not None:
            est += 0.3 * (p - est)                     # recalage sur la position réelle du son
        self._est, self._last_wall = est, now
        # tant que le son joue, on reste dans le morceau : sa fin n'est jamais coupée
        return min(est, self._audio_end - 0.001)

    def _tick(self):
        if not self.playing or self.closed:
            return
        now = time.time()
        if self.mci_playing:
            t = self._audio_time(now)
            if t is None:                      # le son a joué jusqu'au bout du morceau
                t = self._audio_end
        else:
            t = self._play_media + (now - self._play_wall)

        if self._segment_at(t) is None:
            nxt = self._next_valid(t)
            if nxt is None:                    # fin du dernier morceau
                self.pause()
                self.t = self.segs[-1][1]
                self.show_frame()
                self._draw_playhead()
                return
            t = nxt                            # saute la partie supprimée
            self._start_audio(t)
            self._play_wall, self._play_media = time.time(), t
        self.t = t
        self.show_frame()
        self._draw_playhead()
        self.win.after(10, self._tick)

    # ----- édition -----
    def split(self):
        self.segments[self.index] = [list(s) for s in _seg_split(self.segs, self.t)]
        self.sel_seg = None
        self.redraw()

    def delete(self):
        if self.sel_range:
            a, b = self.sel_range
            self.segments[self.index] = [list(s) for s in _seg_subtract(self.segs, a, b)]
            self.sel_range = None
        elif self.sel_seg is not None and self.sel_seg < len(self.segs):
            del self.segs[self.sel_seg]
            self.sel_seg = None
        else:
            self.status.set("Sélectionne d'abord une zone (Maj + glisser) "
                            "ou clique sur un morceau.")
            return
        self.status.set("")
        self.redraw()

    def mark_in(self):
        k = self._segment_at(self.t)
        if k is not None and self.t < self.segs[k][1] - MONTAGE_MIN_SEGMENT:
            self.segs[k][0] = self.t
            self.redraw()

    def mark_out(self):
        for k, (s, e) in enumerate(self.segs):
            if s + MONTAGE_MIN_SEGMENT < self.t <= e:
                self.segs[k][1] = self.t
                self.redraw()
                return

    def reset(self):
        self.segments[self.index] = [[0.0, self.dur]]
        self.sel_seg = self.sel_range = None
        self.redraw()

    def on_key(self, event):
        key = event.keysym
        shift = bool(event.state & 1)
        if key in ("Return", "KP_Enter"):
            self.next()
        elif key == "space":
            self.toggle_play()
        elif key in ("Left", "Right"):
            self.pause()
            step = 1.0 if shift else 1.0 / MONTAGE_PREVIEW_FPS
            self.seek(self.t + (step if key == "Right" else -step))
        elif key in ("Delete", "BackSpace"):
            self.delete()
        elif key.lower() == "c":
            self.split()
        elif key.lower() == "i":
            self.mark_in()
        elif key.lower() == "o":
            self.mark_out()
        elif key.lower() == "r":
            self.reset()


def cmd_montage(args):
    args = [a.strip().strip('"') for a in args]
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError(
            "FFmpeg introuvable : installe-le et ajoute ffmpeg/ffprobe au PATH."
        )

    folder = Path(args[0]) if args else Path(VIDEO_FOLDER)
    out_path = Path(args[1]) if len(args) > 1 else Path("montage.mp4")
    if not folder.is_dir():
        raise RuntimeError(f"Dossier introuvable : {folder}")

    files = sorted(
        (p for p in folder.iterdir()
         if p.is_file() and p.stem.isdigit() and p.suffix.lower() in _MONTAGE_EXTS),
        key=lambda p: int(p.stem),
    )
    if not files:
        raise RuntimeError(f"Aucune vidéo numérotée (1.mp4, 2.mp4...) dans {folder}")

    max_w, max_h, thumb_target = 640, 380, 64
    clips = []
    for path in files:
        try:
            duration, has_audio, (w, h) = _probe_clip(path)
        except Exception as exc:
            terminal_print(f"{path.name} ignorée (illisible) : {exc}", "#ffaa00")
            continue
        scale = min(max_w / w, max_h / h, 1.0)
        fw, fh = max(2, int(w * scale) // 2 * 2), max(2, int(h * scale) // 2 * 2)
        factor = max(1, round(fh / thumb_target))
        clips.append({
            "path": path, "duration": duration, "has_audio": has_audio,
            "size": (w, h), "disp": (fw, fh), "disp_max_h": max_h,
            "thumb_factor": factor, "thumb_h": fh // factor,
        })
    if not clips:
        raise RuntimeError("Aucune vidéo lisible.")

    terminal_print(f"{len(clips)} vidéo(s) chargée(s) : fenêtre de montage ouverte.",
                   "#55ff55")
    MontageEditor(folder, out_path, clips)


# ============================================================
# LANGAGE CD : EDITEUR ET EXECUTION DE SCRIPTS
# ============================================================

cd_editors = []


def cd_command_runner(log):
    def run_line(line, env, interpreter):
        expanded = line
        if env:
            # Une seule passe, avec une fonction de remplacement : les valeurs
            # (chemins Windows avec « \ », texte contenant le nom d'une autre
            # variable...) sont insérées telles quelles, sans être réinterprétées.
            names = sorted(env, key=len, reverse=True)
            pattern = re.compile(
                r'(?<![\w\[])\b(?:' + '|'.join(re.escape(n) for n in names)
                + r')\b(?![\w\]])'
            )
            expanded = pattern.sub(
                lambda m: shlex.quote(str(env[m.group(0)])), line
            )
        try:
            parts = shlex.split(expanded)
        except ValueError as exc:
            raise RuntimeError(f"Arguments de commande invalides : {exc}")
        if not parts:
            return
        command, args = parts[0].lower(), parts[1:]
        if command == 'print':
            log(' '.join(args))
        elif command in COMMANDS:
            # Les commandes longues (gen_image, save, delflow...) travaillent dans
            # un thread et rendent la main tout de suite. Dans un script CD on
            # attend la fin de ces threads avant de passer à la ligne suivante.
            before = set(threading.enumerate())
            result = COMMANDS[command](args)
            wait_for_new_threads(before)
            return result  # permet : variable = commande args
        else:
            raise RuntimeError(f"Commande CD inconnue : {command}")
    return run_line


def wait_for_new_threads(before):
    """Attend la fin des threads lancés depuis `before`, sans geler l'interface.

    On ne peut pas faire un simple join() dans le thread Tk : les threads de
    travail écrivent dans le terminal via Tk, ce qui bloquerait (deadlock).
    On fait donc tourner la boucle d'événements pendant l'attente.
    """
    new_threads = [t for t in threading.enumerate()
                   if t not in before and t.is_alive()]
    on_main = threading.current_thread() is threading.main_thread()
    for t in new_threads:
        while t.is_alive():
            if on_main:
                try:
                    root.update()
                except tk.TclError:  # fenêtre fermée pendant l'attente
                    return
                time.sleep(0.05)
            else:
                t.join(0.2)


def create_cd_interpreter(log):
    return CDInterpreter(
        cd_command_runner(log), log,
        is_command=lambda name: name.lower() in COMMANDS
    )


# ============================================================
# pick : choisit une image par scène et renvoie leurs chemins
# ============================================================
# Utilisation :
#   pick 1 3 2                  -> scène 1 : image A, scène 2 : image C, scène 3 : image B
#   pick 4-6 1 3 2              -> scènes 4 à 6 : A, C, B   (intervalle de scènes)
#   pick 4- 1 3 2               -> à partir de la scène 4, autant de scènes que de choix
#   pick "dossier" 4-6 1 3 2    -> même chose dans un autre dossier (défaut : flow_media)
#
# Sans intervalle, on commence à la scène 1 (comportement d'origine).
# Avec "a-b", il faut exactement (b - a + 1) choix.
#
# Dans un script CD, le résultat se stocke dans un tableau :
#   images = pick 4-6 1 3 2
#   print(images[0])
#
# Les chemins sont relatifs au dossier courant du terminal.

_PICK_RANGE = re.compile(r"^(\d+)-(\d*)$")


def cmd_pick(args):
    args = [a.strip().strip('"') for a in args]
    folder = Path("flow_media")

    # Un premier argument qui n'est ni un chiffre ni un intervalle = dossier
    if args and not args[0].isdigit() and not _PICK_RANGE.match(args[0]):
        folder = Path(args[0])
        args = args[1:]

    # Intervalle de scènes optionnel : "4-6" ou "4-"
    first_scene = 1
    last_scene = None
    if args:
        m = _PICK_RANGE.match(args[0])
        if m:
            first_scene = int(m.group(1))
            last_scene = int(m.group(2)) if m.group(2) else None
            args = args[1:]

    if not args:
        terminal_print('Usage : pick [a-b] 1 3 2   (un chiffre 1-3 par scène : A, B ou C)',
                       "#ffaa00")
        terminal_print('Exemples : pick 1 3 2   |   pick 4-6 2 1 3', "#ffaa00")
        return None

    if first_scene < 1:
        raise RuntimeError("Les scènes commencent à 1.")
    if last_scene is None:
        last_scene = first_scene + len(args) - 1
    if last_scene < first_scene:
        raise RuntimeError(
            f"Intervalle invalide : {first_scene}-{last_scene}."
        )
    expected = last_scene - first_scene + 1
    if len(args) != expected:
        raise RuntimeError(
            f"Scènes {first_scene} à {last_scene} : {expected} choix attendus, "
            f"{len(args)} reçu(s)."
        )

    if not folder.is_dir():
        raise RuntimeError(f"Dossier introuvable : {folder}")

    paths = []
    for scene, choice in zip(range(first_scene, last_scene + 1), args):
        if choice not in ("1", "2", "3"):
            raise RuntimeError(
                f"Scène {scene} : « {choice} » invalide, choisis 1, 2 ou 3."
            )
        letter = "ABC"[int(choice) - 1]
        matches = sorted(folder.glob(f"scene_{scene}_{letter}.*"))
        if not matches:
            raise RuntimeError(
                f"Image introuvable : scene_{scene}_{letter} dans {folder}"
            )
        paths.append(os.path.relpath(matches[0]))

    for p in paths:
        terminal_print(p, "#55ff55")
    return paths


def cmd_cedit(args):
    editor = CDEditor(root, create_cd_interpreter)
    cd_editors.append(editor)
    if args:
        path = Path(" ".join(args)).expanduser()

        # Si on tape `cedit script`, le fichier visé est `script.cd` :
        # on teste l'existence APRÈS avoir ajouté l'extension, sinon un
        # `script.cd` existant était ouvert vide puis écrasé à l'enregistrement.
        if not path.exists() and path.suffix.lower() != '.cd':
            with_ext = path.with_name(path.name + '.cd')
            if with_ext.exists():
                path = with_ext

        if path.exists():
            try:
                content = path.read_text(encoding='utf-8-sig')
            except Exception as exc:
                terminal_print(f"Impossible de lire {path} : {exc}", "#ff5555")
                editor.window.destroy()
                cd_editors.remove(editor)
                return
            editor.path = path
            editor.text.insert('1.0', content)
            editor.text.edit_modified(False)
            editor.name.configure(text=path.name)
            editor.window.title(f"{EDITOR_NAME} — {path.name}")
            editor.highlight()
        else:
            editor.path = path if path.suffix.lower() == '.cd' else path.with_name(path.name + '.cd')
            editor.name.configure(text=editor.path.name + " (nouveau)")
            editor.window.title(f"{EDITOR_NAME} — {editor.path.name} (nouveau)")


def cmd_run_cd(args):
    if len(args) != 1:
        terminal_print('Usage : run fichier.cd', '#ffaa00')
        return
    path = Path(args[0]).expanduser()
    if not path.exists() or path.suffix.lower() != '.cd':
        terminal_print('Fichier .cd introuvable.', '#ff5555')
        return
    try:
        create_cd_interpreter(terminal_print).run(path.read_text(encoding='utf-8'))
        terminal_print('Script CD terminé.', '#00ff88')
    except Exception as exc:
        terminal_print(f'Erreur CD : {exc}', '#ff5555')


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
    "fivi": cmd_fivi,
    "about": cmd_about,
    "info": cmd_info,

    "cinit": cmd_cinit,
    "copen": cmd_copen,
    "tik": cmd_tik,
    "cresce": cmd_cresce,
    "cproject": cmd_cproject,
    "gen_image": cmd_gen_image,
    "save": cmd_save,
    "save_video": cmd_save_video,
    "montage": cmd_montage,
    "delflow": cmd_delflow,
    "gen_video": cmd_gen_video,
    "pick": cmd_pick,

    "cedit": cmd_cedit,
    "run": cmd_run_cd,
}


# ============================================================
# HELP
# ============================================================

def cmd_help(args):
    terminal_print("")
    terminal_print("===== COMMANDES DISPONIBLES =====", "#00ff88")
    terminal_print("")
    for command in COMMANDS:
        terminal_print(f"  {command}")
    terminal_print("")
    terminal_print("exit / quit  -> fermer cet onglet", "#ffaa00")
    terminal_print("term / tab   -> nouvel onglet (ou Ctrl+T)", "#ffaa00")
    terminal_print("Ctrl+W ferme l'onglet · Ctrl+Tab change d'onglet · Alt+1..9 va à l'onglet n", "#ffaa00")
    terminal_print("")


COMMANDS["help"] = cmd_help


# ============================================================
# ONGLETS
# ============================================================

def _terminal_launch_command():
    if getattr(sys, "frozen", False):                 # application empaquetée (.exe)
        return [sys.executable]
    return [sys.executable, str(Path(sys.argv[0] or __file__).resolve())]


def cmd_term(args):
    """Ouvre un nouvel onglet (dans le dossier courant)."""
    _emit({"e": "new_tab"})


COMMANDS["term"] = cmd_term
COMMANDS["tab"] = cmd_term


# ============================================================
# HISTORIQUE PERSISTANT (partagé entre tous les onglets)
# ============================================================

HISTORY_FILE = Path.home() / ".clem_terminal_history.json"
HISTORY_LIMIT = 500


def load_command_history():
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


command_history = load_command_history()


def save_command_history():
    # Les onglets (et plusieurs fenêtres) partagent ce fichier : on y AJOUTE la dernière
    # commande au lieu de l'écraser avec l'historique d'un seul onglet.
    try:
        merged = load_command_history()
        if command_history and (not merged or merged[-1] != command_history[-1]):
            merged.append(command_history[-1])
        HISTORY_FILE.write_text(
            json.dumps(merged[-HISTORY_LIMIT:], ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except OSError as exc:
        terminal_print(f"Impossible de sauvegarder l'historique : {exc}", "#ffaa00")


# ============================================================
# MOTEUR D'UN ONGLET (processus « worker », sans fenêtre)
# ============================================================
# Chaque onglet fait tourner ce moteur dans son propre processus : dossier courant
# indépendant, commandes en parallèle d'un onglet à l'autre. Il reçoit les commandes
# sur son entrée standard et renvoie son affichage sous forme de lignes JSON.

def _emit_cwd():
    _emit({"e": "cwd", "path": os.getcwd()})


def run_command_line(command_line):
    command_line = command_line.strip()
    if not command_line:
        return

    terminal_print(f"{os.getcwd()} > {command_line}", PROMPT_COLOR)

    try:
        parts = shlex.split(command_line)
    except ValueError:
        terminal_print("Erreur : guillemets incorrects.", "#ff5555")
        return
    if not parts:
        return

    command, args = parts[0], parts[1:]

    if command.lower() in ("exit", "quit"):
        _emit({"e": "close"})                  # ferme l'onglet
        return

    if command.lower() in COMMANDS:
        try:
            COMMANDS[command.lower()](args)
        except Exception as e:
            terminal_print(f"Erreur : {e}", "#ff5555")
    else:
        terminal_print(f"Commande inconnue : {command}", "#ff5555")
        terminal_print("Tape 'help' pour voir les commandes.", "#ffaa00")

    _emit_cwd()


def worker_main():
    global root, _proto_out

    # fd 1 est réservé au protocole : tout autre affichage (print, bibliothèques,
    # programmes lancés) part vers la sortie d'erreur et ne peut pas le corrompre.
    proto_fd = os.dup(1)
    os.dup2(2, 1)
    _proto_out = os.fdopen(proto_fd, "w", encoding="utf-8", newline="\n")

    root = tk.Tk()
    root.withdraw()          # le moteur n'a pas de fenêtre : l'affichage est dans l'onglet

    terminal_print("========================================", "#00ff88")
    terminal_print("          CLEM TERMINAL", "#00ff88")
    terminal_print("========================================", "#00ff88")
    terminal_print("")
    terminal_print("Tape 'help' pour voir les commandes.", "#aaaaaa")
    terminal_print("")
    terminal_print(f"Dossier actuel : {os.getcwd()}", PROMPT_COLOR)
    terminal_print("")
    _emit_cwd()
    _emit({"e": "ready"})

    def reader():
        for raw in sys.stdin.buffer:
            try:
                message = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            if "cmd" in message:
                root.after(0, lambda c=message["cmd"]: run_command_line(c))
            elif message.get("exit"):
                break
        root.after(0, root.quit)     # l'onglet est fermé : le moteur s'arrête

    threading.Thread(target=reader, daemon=True).start()
    root.mainloop()


# ============================================================
# FENÊTRE À ONGLETS
# ============================================================
# Raccourcis : Ctrl+T (ou Ctrl+N, ou la commande « term ») nouvel onglet · Ctrl+W ferme
# l'onglet · Ctrl+Tab / Ctrl+Maj+Tab changent d'onglet · Alt+1..9 va à l'onglet n.

class TerminalTab:
    def __init__(self, app, start_cwd):
        self.app = app
        self.cwd = start_cwd
        self.closed = False
        self.dead = False
        self.unread = False
        self.exit_seen = None
        self.stderr_tail = collections.deque(maxlen=30)
        self.history_index = len(command_history)
        self.history_draft = ""
        self.tab_matches, self.tab_index, self.tab_original = [], 0, ""

        # ---- interface de l'onglet ----
        self.frame = tk.Frame(app.content, bg=BG_COLOR)
        terminal_frame = tk.Frame(self.frame, bg=BG_COLOR)
        terminal_frame.pack(fill="both", expand=True, padx=15, pady=(15, 5))
        self.text = tk.Text(terminal_frame, bg=BG_COLOR, fg=TEXT_COLOR,
                            insertbackground=TEXT_COLOR, font=FONT, relief="flat",
                            borderwidth=0, wrap="word")
        self.text.pack(fill="both", expand=True)

        input_frame = tk.Frame(self.frame, bg="#111118")
        input_frame.pack(fill="x", padx=15, pady=15)
        tk.Label(input_frame, text=">", bg="#111118", fg=PROMPT_COLOR,
                 font=("Consolas", 12, "bold")).pack(side="left", padx=(10, 5))
        self.entry = tk.Entry(input_frame, bg=INPUT_COLOR, fg=TEXT_COLOR,
                              insertbackground=TEXT_COLOR, font=FONT, relief="flat")
        self.entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))

        e = self.entry
        e.bind("<Return>", self.submit)
        e.bind("<Tab>", self.complete)
        e.bind("<Up>", self.history_up)
        e.bind("<Down>", self.history_down)
        e.bind("<KeyRelease>", lambda ev: self.reset_completion()
               if ev.keysym not in ("Tab", "Up", "Down") else None)
        # raccourcis d'onglets (« break » : évite par ex. Ctrl+T = inverser deux lettres)
        for keys, action in (
            (("<Control-t>", "<Control-T>", "<Control-n>", "<Control-N>"), app.new_tab),
            (("<Control-w>", "<Control-W>"), lambda: app.close_tab(app.active)),
            (("<Control-Tab>",), lambda: app.cycle(+1)),
            (("<Control-Shift-Tab>", "<Control-ISO_Left_Tab>"), lambda: app.cycle(-1)),
        ):
            for key in keys:
                try:
                    e.bind(key, lambda ev, a=action: (a(), "break")[1])
                except tk.TclError:      # touche inconnue sur ce système (ex : ISO_Left_Tab sous Windows)
                    pass
        for n in range(1, 10):
            try:
                e.bind(f"<Alt-Key-{n}>", lambda ev, n=n: (app.goto(n - 1), "break")[1])
            except tk.TclError:
                pass

        # ---- moteur de l'onglet : un processus dédié ----
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        kwargs = {"stdin": subprocess.PIPE, "stdout": subprocess.PIPE,
                  "stderr": subprocess.PIPE, "env": env}
        if platform.system() == "Windows":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        cwd = start_cwd if os.path.isdir(start_cwd) else str(Path.home())
        self.proc = subprocess.Popen(_terminal_launch_command() + ["--worker"],
                                     cwd=cwd, **kwargs)
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    # ----- moteur : lecture des événements -----
    def _read_stdout(self):
        for raw in self.proc.stdout:
            try:
                event = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            self.app.events.put((self, event))
        self.app.events.put((self, {"e": "eof"}))

    def _read_stderr(self):
        for raw in self.proc.stderr:
            self.stderr_tail.append(raw.decode("utf-8", "replace").rstrip())

    def handle(self, event):
        kind = event.get("e")
        if kind == "print":
            self.write(event.get("text", ""), event.get("color"))
            if self is not self.app.active and not self.unread:
                self.unread = True
                self.app.refresh_tabs()
        elif kind == "clear":
            self.text.delete("1.0", tk.END)
        elif kind == "cwd":
            self.cwd = event.get("path", self.cwd)
            self.app.refresh_tabs()
        elif kind == "new_tab":
            self.app.new_tab(self.cwd)
        elif kind == "close":
            self.app.close_tab(self)
        elif kind == "eof":
            self.mark_dead()

    def mark_dead(self):
        if self.dead or self.closed:
            return
        self.dead = True
        code = self.proc.poll()
        self.write(f"Le moteur de cet onglet s'est arrêté (code {code}).", "#ff5555")
        for line in list(self.stderr_tail)[-8:]:
            self.write(line, "#ff5555")
        self.write("Ferme l'onglet (Ctrl+W) et ouvres-en un nouveau (Ctrl+T).", "#ffaa00")

    def write(self, text, color=None):
        self.text.insert(tk.END, text + "\n")
        if color:
            tag = f"color_{color.replace('#', '')}"
            self.text.tag_config(tag, foreground=color)
            self.text.tag_add(tag, self.text.index("end-2l"), self.text.index("end-1l"))
        self.text.see(tk.END)

    def send(self, message):
        try:
            self.proc.stdin.write((json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8"))
            self.proc.stdin.flush()
            return True
        except (OSError, ValueError):
            return False

    def shutdown(self):
        """Ferme le moteur : arrêt propre, puis forcé s'il ne répond pas."""
        self.closed = True
        self.send({"exit": True})
        proc = self.proc

        def force():
            if proc.poll() is None:
                try:
                    proc.kill()
                except OSError:
                    pass
        root.after(1500, force)

    # ----- saisie -----
    def submit(self, event=None):
        line = self.entry.get().strip()
        if not line:
            return "break"
        if not command_history or command_history[-1] != line:
            command_history.append(line)
            command_history[:] = command_history[-HISTORY_LIMIT:]
            save_command_history()
        self.history_index = len(command_history)
        self.history_draft = ""
        self.reset_completion()
        self.entry.delete(0, tk.END)
        if self.dead or not self.send({"cmd": line}):
            self.write("Cet onglet est arrêté : ouvre-en un nouveau (Ctrl+T).", "#ffaa00")
        return "break"

    def reset_completion(self):
        self.tab_matches, self.tab_index, self.tab_original = [], 0, ""

    def complete(self, event=None):
        """Complète les commandes et les chemins (relatifs au dossier de CET onglet)."""
        entry = self.entry
        current = entry.get()
        cursor = entry.index(tk.INSERT)
        before = current[:cursor]
        token_start = max(before.rfind(" "), before.rfind("\t")) + 1
        raw_token = before[token_start:]
        quote = raw_token[:1] if raw_token[:1] in ("'", '"') else ""
        token = raw_token[1:] if quote else raw_token

        if not self.tab_matches or self.tab_original != current:
            self.tab_original = current
            self.tab_index = 0
            if token_start == 0 and not any(sep in token for sep in (os.sep, "/", "\\")):
                candidates = [name for name in COMMANDS if name.startswith(token.lower())]
            else:
                expanded = os.path.expanduser(token)
                directory_part = os.path.dirname(expanded)
                basename = os.path.basename(expanded)
                search_dir = Path(self.cwd) / directory_part if directory_part else Path(self.cwd)
                try:
                    entries = list(search_dir.iterdir())
                except (OSError, PermissionError):
                    entries = []
                candidates = []
                for item in entries:
                    if item.name.lower().startswith(basename.lower()):
                        candidate = (str(Path(directory_part) / item.name)
                                     if directory_part else item.name)
                        if item.is_dir():
                            candidate += os.sep
                        candidates.append(candidate)
                candidates.sort(key=str.lower)
            self.tab_matches = candidates

        if not self.tab_matches:
            return "break"

        candidate = self.tab_matches[self.tab_index % len(self.tab_matches)]
        self.tab_index += 1
        if quote:
            candidate = quote + candidate
            if not candidate.endswith(os.sep):
                candidate += quote
        elif " " in candidate:
            candidate = '"' + candidate + ('"' if not candidate.endswith(os.sep) else '')
        entry.delete(0, tk.END)
        entry.insert(0, current[:token_start] + candidate + current[cursor:])
        entry.icursor(token_start + len(candidate))
        return "break"

    def history_up(self, event=None):
        if not command_history:
            return "break"
        if self.history_index == len(command_history):
            self.history_draft = self.entry.get()
        if self.history_index > 0:
            self.history_index -= 1
        self.entry.delete(0, tk.END)
        self.entry.insert(0, command_history[self.history_index])
        self.entry.icursor(tk.END)
        self.reset_completion()
        return "break"

    def history_down(self, event=None):
        if self.history_index < len(command_history):
            self.history_index += 1
        self.entry.delete(0, tk.END)
        self.entry.insert(0, command_history[self.history_index]
                          if self.history_index < len(command_history) else self.history_draft)
        self.entry.icursor(tk.END)
        self.reset_completion()
        return "break"


class TerminalApp:
    BAR_BG, TAB_BG, TAB_ACTIVE = "#0d0d12", "#15151c", "#262633"

    def __init__(self):
        global root, background_label
        self.tabs = []
        self.active = None
        self.events = queue.Queue()

        root = tk.Tk()
        root.title(WINDOW_TITLE)
        root.geometry("1000x650")
        root.minsize(700, 450)
        root.configure(bg=BG_COLOR)

        background_label = tk.Label(root, bg=BG_COLOR)
        background_label.place(x=0, y=0, relwidth=1, relheight=1)

        top_bar = tk.Frame(root, bg="#111118", height=45)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)
        tk.Label(top_bar, text="  CLEM TERMINAL", bg="#111118", fg="#ffffff",
                 font=("Consolas", 12, "bold")).pack(side="left", padx=10)
        tk.Button(top_bar, text="Fond", command=choose_background, bg="#20202a", fg="white",
                  activebackground="#30303a", activeforeground="white", relief="flat",
                  padx=12).pack(side="right", padx=10)

        self.tabbar = tk.Frame(root, bg=self.BAR_BG)
        self.tabbar.pack(fill="x")
        self.content = tk.Frame(root, bg=BG_COLOR)
        self.content.pack(fill="both", expand=True)

        root.protocol("WM_DELETE_WINDOW", self.quit)
        self.new_tab(os.getcwd())
        root.after(30, self.poll)

    # ----- événements des moteurs -----
    def poll(self):
        for _ in range(500):
            try:
                tab, event = self.events.get_nowait()
            except queue.Empty:
                break
            if not tab.closed:
                tab.handle(event)
        for tab in list(self.tabs):          # moteur disparu sans fermer son flux
            if not tab.dead and tab.proc.poll() is not None:
                tab.exit_seen = tab.exit_seen or time.time()
                if time.time() - tab.exit_seen > 1.0:
                    tab.mark_dead()
        root.after(30, self.poll)

    # ----- gestion des onglets -----
    def new_tab(self, start_cwd=None):
        if not isinstance(start_cwd, str):
            start_cwd = self.active.cwd if self.active else os.getcwd()
        tab = TerminalTab(self, start_cwd)
        self.tabs.append(tab)
        self.select(tab)
        return tab

    def select(self, tab):
        if self.active is not None and self.active is not tab:
            self.active.frame.pack_forget()
        self.active = tab
        tab.unread = False
        tab.frame.pack(fill="both", expand=True)
        tab.entry.focus_set()
        tab.text.see(tk.END)
        self.refresh_tabs()

    def goto(self, index):
        if 0 <= index < len(self.tabs):
            self.select(self.tabs[index])

    def cycle(self, step):
        if self.tabs:
            self.select(self.tabs[(self.tabs.index(self.active) + step) % len(self.tabs)])

    def close_tab(self, tab):
        if tab is None or tab not in self.tabs:
            return
        index = self.tabs.index(tab)
        self.tabs.remove(tab)
        tab.shutdown()
        tab.frame.destroy()
        if not self.tabs:
            root.destroy()
            return
        if tab is self.active:
            self.active = None
            self.select(self.tabs[min(index, len(self.tabs) - 1)])
        else:
            self.refresh_tabs()

    def quit(self):
        for tab in self.tabs:
            tab.closed = True
            try:
                tab.proc.kill()
            except OSError:
                pass
        root.destroy()

    def active_write(self, text, color=None):
        if self.active is not None:
            self.active.write(text, color)

    # ----- barre d'onglets -----
    def refresh_tabs(self):
        for child in self.tabbar.winfo_children():
            child.destroy()
        for i, tab in enumerate(self.tabs):
            is_active = tab is self.active
            bg = self.TAB_ACTIVE if is_active else self.TAB_BG
            box = tk.Frame(self.tabbar, bg=bg)
            box.pack(side="left", padx=(6 if i == 0 else 2, 0), pady=(6, 0))
            name = Path(tab.cwd).name or tab.cwd
            label = tk.Label(box, text=f" {i + 1}  {name}{'  •' if tab.unread else ''} ",
                             bg=bg, fg="#ffffff" if is_active else "#9a9aa8",
                             font=("Consolas", 10), cursor="hand2")
            label.pack(side="left", pady=(4, 4))
            close = tk.Label(box, text="✕ ", bg=bg, fg="#9a9aa8", font=("Consolas", 10),
                             cursor="hand2")
            close.pack(side="left")
            for widget in (box, label):
                widget.bind("<Button-1>", lambda ev, t=tab: self.select(t))
                widget.bind("<Button-2>", lambda ev, t=tab: self.close_tab(t))
            close.bind("<Button-1>", lambda ev, t=tab: self.close_tab(t))
            close.bind("<Enter>", lambda ev, w=close: w.config(fg=PROMPT_COLOR))
            close.bind("<Leave>", lambda ev, w=close: w.config(fg="#9a9aa8"))
            if is_active:
                tk.Frame(box, bg=PROMPT_COLOR, height=2).place(relx=0, rely=1.0,
                                                               relwidth=1, anchor="sw")
        plus = tk.Label(self.tabbar, text=" + ", bg=self.BAR_BG, fg="#ffffff",
                        font=("Consolas", 12, "bold"), cursor="hand2")
        plus.pack(side="left", padx=(6, 0), pady=(6, 0))
        plus.bind("<Button-1>", lambda ev: self.new_tab())
        if self.active is not None:
            root.title(f"{WINDOW_TITLE} — {self.active.cwd}")


def choose_background():
    global background_image

    filename = filedialog.askopenfilename(
        title="Choisir une image",
        filetypes=[
            ("Images", "*.png *.jpg *.jpeg *.gif"),
            ("Tous les fichiers", "*.*"),
        ]
    )

    if not filename:
        return

    try:
        background_image = tk.PhotoImage(file=filename)
        background_label.configure(image=background_image)
    except Exception:
        terminal_print("Erreur : image non compatible.", "#ff5555")


background_image = None
background_label = None


def manager_main():
    global _manager_sink
    app = TerminalApp()
    _manager_sink = app.active_write
    root.mainloop()


# ============================================================
# LANCEMENT
# ============================================================

if WORKER_MODE:
    worker_main()
else:
    manager_main()