import tkinter as tk
from tkinter import filedialog
import os
import re
import shutil
import platform
import json
import subprocess
import shlex
import socket
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

def terminal_print(text="", color=None):
    terminal.insert(tk.END, text + "\n")

    if color:
        tag_name = f"color_{color.replace('#', '')}"
        terminal.tag_config(tag_name, foreground=color)
        start = terminal.index("end-2l")
        end = terminal.index("end-1l")
        terminal.tag_add(tag_name, start, end)

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
    terminal.delete("1.0", tk.END)


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

    terminal_print(lines[n - 1].replace("{", "").replace("}", "").strip())


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
# Corrections :
#   - le vrai conteneur de défilement est .page-container
#     ([cdkvirtualscrollingelement]) et non cdk-virtual-scroll-viewport
#   - les tuiles vidéo n'ont pas de <video> dans le DOM tant qu'on ne les
#     survole / ouvre pas : on déclenche le survol puis l'ouverture
#   - tout est repéré par la structure de la page (indépendant de la langue)
#   - le port Chrome est relu après le lancement (plus de décalage de port)
#   - les fichiers déjà présents sont ignorés

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
    """Nom de fichier stable (sans extension) pour une image ou une vidéo.

    Pour les vidéos on se base sur la miniature (stable) plutôt que sur l'URL
    de la vidéo, qui peut être signée et changer d'une session à l'autre.
    """
    if item["id"]:
        return item["id"]
    base = item.get("thumb") or item.get("title") or item["url"]
    digest = _hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]
    return f"video_{digest}"


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

            n_img = sum(1 for i in items if i["type"] == "image")
            n_vid = sum(1 for i in items if i["type"] == "video")
            log(f"{len(items)} média(s) trouvé(s) : {n_img} image(s), "
                f"{n_vid} vidéo(s).", "#55ff55")

            if not items:
                log("Rien à sauvegarder.", "#ffaa00")
                _flow_dump(driver, "save_empty", log)
                return

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

            for n, item in enumerate(items, 1):
                name = _flow_media_name(item)
                label = "vidéo" if item["type"] == "video" else "image"

                # Déjà sauvegardé ? (quelle que soit l'extension)
                if any(folder.glob(name + ".*")):
                    skipped += 1
                    log(f"[{n}/{len(items)}] {label} déjà présente : {name}", "#888888")
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
                    log(f"[{n}/{len(items)}] Échec {label} {name} : {last_err}", "#ff5555")
                    continue

                ext = _flow_ext(data, content_type, item["type"])
                path = folder / (name + ext)
                path.write_bytes(data)
                saved += 1
                size_kb = len(data) / 1024
                log(f"[{n}/{len(items)}] {label} sauvegardée : "
                    f"{path.name} ({size_kb:,.0f} Ko)", "#55ff55")

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

            log("Lancement de Veo 3.1...", "#55aaff")
            driver.execute_script("arguments[0].click();", generate_button)
            log("Génération lancée ! Format vertical 9:16, 1 vidéo.", "#55ff55")

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
# LANGAGE CD : EDITEUR ET EXECUTION DE SCRIPTS
# ============================================================

cd_editors = []


def cd_command_runner(log):
    def run_line(line, env, interpreter):
        expanded = line
        for name in sorted(env, key=len, reverse=True):
            value = env[name]
            replacement = shlex.quote(str(value))
            expanded = re.sub(
                rf'(?<![\w\[])\b{re.escape(name)}\b(?![\w\]])',
                replacement, expanded
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
            COMMANDS[command](args)
        else:
            raise RuntimeError(f"Commande CD inconnue : {command}")
    return run_line


def create_cd_interpreter(log):
    return CDInterpreter(cd_command_runner(log), log)


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
    "delflow": cmd_delflow,
    "gen_video": cmd_gen_video,

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
    terminal_print("exit / quit  -> fermer le terminal", "#ffaa00")
    terminal_print("")


COMMANDS["help"] = cmd_help


# ============================================================
# HISTORIQUE PERSISTANT + AUTOCOMPLÉTION
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
history_index = len(command_history)
history_draft = ""
tab_matches = []
tab_index = 0
tab_original = ""


def save_command_history():
    try:
        HISTORY_FILE.write_text(
            json.dumps(command_history[-HISTORY_LIMIT:], ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except OSError as exc:
        terminal_print(f"Impossible de sauvegarder l'historique : {exc}", "#ffaa00")


def reset_completion():
    global tab_matches, tab_index, tab_original
    tab_matches = []
    tab_index = 0
    tab_original = ""


def complete_command(event=None):
    """Complète les commandes et les chemins de fichiers/dossiers avec Tab."""
    global tab_matches, tab_index, tab_original
    current = command_entry.get()
    cursor = command_entry.index(tk.INSERT)
    before = current[:cursor]
    token_start = max(before.rfind(" "), before.rfind("\t")) + 1
    raw_token = before[token_start:]
    quote = raw_token[:1] if raw_token[:1] in ("'", '"') else ""
    token = raw_token[1:] if quote else raw_token

    if not tab_matches or tab_original != current:
        tab_original = current
        tab_index = 0
        if token_start == 0 and not any(sep in token for sep in (os.sep, "/", "\\")):
            candidates = [name for name in COMMANDS if name.startswith(token.lower())]
        else:
            expanded = os.path.expanduser(token)
            directory_part = os.path.dirname(expanded)
            basename = os.path.basename(expanded)
            search_dir = Path(directory_part) if directory_part else Path.cwd()
            try:
                entries = list(search_dir.iterdir())
            except (OSError, PermissionError):
                entries = []
            candidates = []
            for entry in entries:
                if entry.name.lower().startswith(basename.lower()):
                    candidate = (str(Path(directory_part) / entry.name)
                                 if directory_part else entry.name)
                    if entry.is_dir():
                        candidate += os.sep
                    candidates.append(candidate)
            candidates.sort(key=str.lower)
        tab_matches = candidates

    if not tab_matches:
        return "break"

    candidate = tab_matches[tab_index % len(tab_matches)]
    tab_index += 1
    if quote:
        candidate = quote + candidate
        if not candidate.endswith(os.sep):
            candidate += quote
    elif " " in candidate:
        candidate = '"' + candidate + ('"' if not candidate.endswith(os.sep) else '')
    new_value = current[:token_start] + candidate + current[cursor:]
    command_entry.delete(0, tk.END)
    command_entry.insert(0, new_value)
    command_entry.icursor(token_start + len(candidate))
    return "break"


def history_up(event=None):
    global history_index, history_draft
    if not command_history:
        return "break"
    if history_index == len(command_history):
        history_draft = command_entry.get()
    if history_index > 0:
        history_index -= 1
    command_entry.delete(0, tk.END)
    command_entry.insert(0, command_history[history_index])
    command_entry.icursor(tk.END)
    reset_completion()
    return "break"


def history_down(event=None):
    global history_index, history_draft
    if history_index < len(command_history):
        history_index += 1
    command_entry.delete(0, tk.END)
    value = (command_history[history_index]
             if history_index < len(command_history) else history_draft)
    command_entry.insert(0, value)
    command_entry.icursor(tk.END)
    reset_completion()
    return "break"


# ============================================================
# EXÉCUTER UNE COMMANDE
# ============================================================

def execute_command(event=None):
    command_line = command_entry.get().strip()

    if not command_line:
        return

    global history_index, history_draft
    if not command_history or command_history[-1] != command_line:
        command_history.append(command_line)
        command_history[:] = command_history[-HISTORY_LIMIT:]
        save_command_history()
    history_index = len(command_history)
    history_draft = ""
    reset_completion()

    terminal_print(f"{os.getcwd()} > {command_line}", PROMPT_COLOR)

    command_entry.delete(0, tk.END)

    try:
        parts = shlex.split(command_line)
    except ValueError:
        terminal_print("Erreur : guillemets incorrects.", "#ff5555")
        return

    if not parts:
        return

    command = parts[0]
    args = parts[1:]

    if command.lower() in ("exit", "quit"):
        root.destroy()
        return

    if command.lower() in COMMANDS:
        try:
            COMMANDS[command.lower()](args)
        except Exception as e:
            terminal_print(f"Erreur : {e}", "#ff5555")
    else:
        terminal_print(f"Commande inconnue : {command}", "#ff5555")
        terminal_print("Tape 'help' pour voir les commandes.", "#ffaa00")


# ============================================================
# CHOISIR UNE IMAGE DE FOND
# ============================================================

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


# ============================================================
# FENÊTRE PRINCIPALE
# ============================================================

root = tk.Tk()
root.title(WINDOW_TITLE)
root.geometry("1000x650")
root.minsize(700, 450)
root.configure(bg=BG_COLOR)


# ============================================================
# IMAGE DE FOND
# ============================================================

background_image = None

background_label = tk.Label(root, bg=BG_COLOR)
background_label.place(x=0, y=0, relwidth=1, relheight=1)


# ============================================================
# BARRE DU HAUT
# ============================================================

top_bar = tk.Frame(root, bg="#111118", height=45)
top_bar.pack(fill="x")
top_bar.pack_propagate(False)

title = tk.Label(
    top_bar,
    text="  CLEM TERMINAL",
    bg="#111118",
    fg="#ffffff",
    font=("Consolas", 12, "bold")
)
title.pack(side="left", padx=10)

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
background_button.pack(side="right", padx=10)


# ============================================================
# ZONE TERMINAL
# ============================================================

terminal_frame = tk.Frame(root, bg=BG_COLOR)
terminal_frame.pack(fill="both", expand=True, padx=15, pady=(15, 5))

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
terminal.pack(fill="both", expand=True)


# ============================================================
# ZONE DE SAISIE
# ============================================================

input_frame = tk.Frame(root, bg="#111118")
input_frame.pack(fill="x", padx=15, pady=15)

prompt = tk.Label(
    input_frame,
    text=">",
    bg="#111118",
    fg=PROMPT_COLOR,
    font=("Consolas", 12, "bold")
)
prompt.pack(side="left", padx=(10, 5))

command_entry = tk.Entry(
    input_frame,
    bg=INPUT_COLOR,
    fg=TEXT_COLOR,
    insertbackground=TEXT_COLOR,
    font=FONT,
    relief="flat"
)
command_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))

command_entry.bind("<Return>", execute_command)
command_entry.bind("<Tab>", complete_command)
command_entry.bind("<Up>", history_up)
command_entry.bind("<Down>", history_down)
command_entry.bind(
    "<KeyRelease>",
    lambda event: reset_completion() if event.keysym not in ("Tab", "Up", "Down") else None
)


# ============================================================
# MESSAGE DE DÉMARRAGE
# ============================================================

terminal_print("========================================", "#00ff88")
terminal_print("          CLEM TERMINAL", "#00ff88")
terminal_print("========================================", "#00ff88")
terminal_print("")
terminal_print("Tape 'help' pour voir les commandes.", "#aaaaaa")
terminal_print("")
terminal_print(f"Dossier actuel : {os.getcwd()}", PROMPT_COLOR)
terminal_print("")


# ============================================================
# FOCUS + LANCEMENT
# ============================================================

command_entry.focus_set()

root.mainloop()