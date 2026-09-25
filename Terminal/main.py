
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

    import time
    import threading
    import os
    import json

    def tik_worker():

        # ========================================================
        # SELENIUM
        # ========================================================

        try:

            import sys
            import selenium

            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            terminal_print(
                f"Selenium détecté : {selenium.__version__}",
                "#00ff88"
            )

            terminal_print(
                f"Python utilisé : {sys.executable}",
                "#888888"
            )

        except Exception as e:

            terminal_print(
                f"Erreur Selenium : {e}",
                "#ff5555"
            )

            return

        # ========================================================
        # LOCAL STATE CHROME
        # ========================================================

        local_state_path = os.path.expandvars(
            r"%LOCALAPPDATA%\Google\Chrome\User Data\Local State"
        )

        if not os.path.exists(local_state_path):

            terminal_print(
                "Local State de Chrome introuvable.",
                "#ff5555"
            )

            return

        try:

            with open(
                local_state_path,
                "r",
                encoding="utf-8"
            ) as f:

                local_state = json.load(f)

        except Exception as e:

            terminal_print(
                f"Erreur lecture Local State : {e}",
                "#ff5555"
            )

            return

        # ========================================================
        # RECHERCHE DU PROFIL
        # ========================================================

        profile_cache = (
            local_state
            .get("profile", {})
            .get("info_cache", {})
        )

        chrome_profile = None

        for folder_name, profile_data in profile_cache.items():

            name = profile_data.get(
                "name",
                ""
            )

            if name.lower() == args[0].lower():

                chrome_profile = folder_name

                break

        if chrome_profile is None:

            terminal_print(
                f'Profil "{args[0]}" introuvable.',
                "#ff5555"
            )

            terminal_print(
                "Profils disponibles :",
                "#ffaa00"
            )

            for folder_name, profile_data in profile_cache.items():

                name = profile_data.get(
                    "name",
                    folder_name
                )

                terminal_print(
                    f"  - {name} ({folder_name})",
                    "#888888"
                )

            return

        terminal_print(
            f"Profil trouvé : {chrome_profile}",
            "#888888"
        )

        # ========================================================
        # USER DATA
        # ========================================================

        user_data_dir = os.path.expandvars(
            r"%LOCALAPPDATA%\Google\Chrome\User Data"
        )

        # ========================================================
        # URL TIKTOK
        # ========================================================

        tiktok_url = (
            "https://www.tiktok.com/"
            "tiktokstudio/upload"
            "?from=webapp&tab=video"
        )

        # ========================================================
        # OPTIONS CHROME
        # ========================================================

        options = Options()

        options.add_argument(
            f"--user-data-dir={user_data_dir}"
        )

        options.add_argument(
            f"--profile-directory={chrome_profile}"
        )

        options.add_argument(
            "--start-maximized"
        )

        # ========================================================
        # LANCEMENT CHROME PAR SELENIUM
        # ========================================================

        terminal_print(
            f'Lancement du profil "{args[0]}"...',
            "#00ff88"
        )

        try:

            driver = webdriver.Chrome(
                options=options
            )

        except Exception as e:

            terminal_print(
                "Impossible de lancer Chrome avec ce profil.",
                "#ff5555"
            )

            terminal_print(
                str(e),
                "#ff5555"
            )

            terminal_print(
                "",
                "#ffffff"
            )

            terminal_print(
                "IMPORTANT : ferme complètement Chrome",
                "#ffaa00"
            )

            terminal_print(
                "avant de lancer la commande tik.",
                "#ffaa00"
            )

            return

        terminal_print(
            "Chrome lancé avec le vrai profil.",
            "#00ff88"
        )

        # ========================================================
        # OUVERTURE TIKTOK STUDIO
        # ========================================================

        terminal_print(
            "Ouverture de TikTok Studio...",
            "#888888"
        )

        try:

            driver.get(
                tiktok_url
            )

        except Exception as e:

            terminal_print(
                f"Erreur ouverture TikTok : {e}",
                "#ff5555"
            )

            return

        # ========================================================
        # ATTENTE PAGE
        # ========================================================

        try:

            WebDriverWait(
                driver,
                60
            ).until(
                lambda d:
                d.execute_script(
                    "return document.readyState"
                ) == "complete"
            )

        except:

            pass

        terminal_print(
            "Attente du chargement de TikTok...",
            "#888888"
        )

        time.sleep(5)

        # ========================================================
        # RECHERCHE DU BOUTON
        # ========================================================

        terminal_print(
            "Recherche de « Sélectionner une vidéo »...",
            "#888888"
        )

        bouton = None

        # --------------------------------------------------------
        # MÉTHODE 1
        # --------------------------------------------------------

        try:

            bouton = WebDriverWait(
                driver,
                30
            ).until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "button.upload-stage-btn"
                    )
                )
            )

            terminal_print(
                "Bouton trouvé !",
                "#00ff88"
            )

        except:

            pass

        # --------------------------------------------------------
        # MÉTHODE 2
        # --------------------------------------------------------

        if bouton is None:

            try:

                bouton = WebDriverWait(
                    driver,
                    15
                ).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            ".upload-stage-btn"
                        )
                    )
                )

                terminal_print(
                    "Bouton trouvé avec .upload-stage-btn !",
                    "#00ff88"
                )

            except:

                pass

        # --------------------------------------------------------
        # MÉTHODE 3 : TEXTE
        # --------------------------------------------------------

        if bouton is None:

            try:

                elements = driver.find_elements(
                    By.XPATH,
                    "//*[contains("
                    "translate("
                    "normalize-space(.),"
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ',"
                    "'abcdefghijklmnopqrstuvwxyzàâäéèêëîïôöùûüç'"
                    "),"
                    "'sélectionner une vidéo'"
                    ")]"
                )

                for element in elements:

                    try:

                        if element.is_displayed():

                            bouton = element

                            terminal_print(
                                "Bouton trouvé par son texte !",
                                "#00ff88"
                            )

                            break

                    except:

                        pass

            except Exception as e:

                terminal_print(
                    f"Recherche texte échouée : {e}",
                    "#888888"
                )

        # ========================================================
        # BOUTON INTROUVABLE
        # ========================================================

        if bouton is None:

            terminal_print(
                "Bouton introuvable.",
                "#ff5555"
            )

            terminal_print(
                "Voici les boutons détectés :",
                "#ffaa00"
            )

            try:

                buttons = driver.find_elements(
                    By.TAG_NAME,
                    "button"
                )

                for i, button in enumerate(buttons):

                    try:

                        texte = button.text.strip()

                        classe = button.get_attribute(
                            "class"
                        )

                        if texte:

                            terminal_print(
                                f"[{i}] {texte}",
                                "#888888"
                            )

                            terminal_print(
                                f"    {classe}",
                                "#555555"
                            )

                    except:

                        pass

            except:

                pass

            return

        # ========================================================
        # SCROLL
        # ========================================================

        try:

            driver.execute_script(
                """
                arguments[0].scrollIntoView({
                    behavior: 'instant',
                    block: 'center',
                    inline: 'center'
                });
                """,
                bouton
            )

            time.sleep(1)

        except:

            pass

        # ========================================================
        # CLIC 1 : SELENIUM
        # ========================================================

        try:

            bouton.click()

            terminal_print(
                "✓ Bouton cliqué !",
                "#00ff88"
            )

            return

        except Exception as e:

            terminal_print(
                f"Clic Selenium échoué : {e}",
                "#ffaa00"
            )

        # ========================================================
        # CLIC 2 : JAVASCRIPT
        # ========================================================

        try:

            driver.execute_script(
                """
                arguments[0].scrollIntoView({
                    block: 'center',
                    inline: 'center'
                });

                arguments[0].click();
                """,
                bouton
            )

            terminal_print(
                "✓ Bouton cliqué avec JavaScript !",
                "#00ff88"
            )

            return

        except Exception as e:

            terminal_print(
                f"Clic JavaScript échoué : {e}",
                "#ff5555"
            )

    # ============================================================
    # VÉRIFICATION ARGUMENT
    # ============================================================

    if len(args) != 1:

        terminal_print(
            'Usage : tik "Nom du profil Chrome"',
            "#ffaa00"
        )

        return

    # ============================================================
    # THREAD
    # ============================================================

    thread = threading.Thread(
        target=tik_worker,
        daemon=True
    )

    thread.start()


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
