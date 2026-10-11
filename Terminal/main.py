
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

    "tik": cmd_tik,

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
