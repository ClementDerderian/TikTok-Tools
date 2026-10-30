# Documentation du langage CD

## Clem Terminal --- Référence de syntaxe

**Version :** première version\
**Extension des scripts :** `.cd`

Le langage CD permet d'écrire des scripts qui enchaînent les commandes
de Clem Terminal et utilisent des variables, des collections, des
conditions, des boucles et des fonctions.

Un script peut être lancé depuis Clem Terminal avec `run fichier.cd`, ou
ouvert dans Clem Editor avec `cedit fichier.cd` puis exécuté avec
**F5**.

> Cette documentation décrit l'implémentation actuelle de
> `cd_language.py` et son intégration dans `main.py`. Certaines
> fonctionnalités évoquées comme possibles dans le projet ne sont pas
> encore implémentées.

------------------------------------------------------------------------

## 1. Créer et exécuter un script

Créer un fichier portant l'extension `.cd`, par exemple `automation.cd`.

Depuis Clem Terminal :

``` text
cedit automation.cd
```

Cela ouvre le fichier dans Clem Editor. Pour l'exécuter directement :

``` text
run automation.cd
```

Dans l'éditeur, utiliser **Ctrl + S** pour enregistrer et **F5** pour
exécuter le script.

Les chemins relatifs sont interprétés depuis le répertoire de travail
courant du terminal.

## 2. Commentaires

Une ligne dont le premier caractère utile est `#` est ignorée :

``` cd
# Ceci est un commentaire
nom = "Clement"
```

## 3. Variables

Une variable est créée ou modifiée avec `=` :

``` cd
nom = "Clement"
age = 20
prix = 9.99
message = "Bonjour"
```

Les variables sont réutilisables dans les expressions et dans les
commandes du terminal :

``` cd
profil = "Clem"
print(profil)
cresce profil
```

Lorsqu'une variable est utilisée dans une commande du terminal, sa
valeur est substituée dans la ligne de commande.

Les variables créées au niveau principal du script sont globales au
script. Les paramètres et variables créés pendant l'appel d'une fonction
sont locaux à cette fonction.

## 4. Types et expressions

L'interpréteur prend actuellement en charge : - les nombres entiers et
décimaux ; - les chaînes entre guillemets simples ou doubles ; - les
listes et dictionnaires ; - l'accès à un élément avec des crochets ; -
les opérations arithmétiques `+`, `-`, `*`, `/`, `//`, `%` et `**` ; -
les comparaisons `==`, `!=`, `<`, `<=`, `>` et `>=` ; - les opérateurs
logiques `and`, `or` et `not`.

Exemples :

``` cd
a = 10
b = 3
somme = a + b
reste = a % b
puissance = a ** 2

if[somme >= 13]
[
    print("La condition est vraie")
]
```

Les expressions sont évaluées avec une liste d'opérations autorisées ;
le code Python arbitraire n'est pas exécuté comme expression CD.

## 5. Tableaux

Un tableau s'écrit entre deux barres verticales. Les éléments sont
séparés par des virgules :

``` cd
noms = |Alice,Bob,Charlie|
nombres = |10,20,30,40|
```

Un tableau vide s'écrit `||`.

L'indexation commence à zéro :

``` cd
print(noms[0])
print(nombres[2])
```

On peut aussi affecter un élément existant :

``` cd
nombres[1] = 99
```

Les éléments peuvent être des expressions simples, des variables ou des
chaînes entre guillemets.

## 6. Dictionnaires

Un dictionnaire utilise la même paire de barres verticales. Les entrées
sont séparées par des points-virgules et chaque entrée suit la forme
`cle:valeur` :

``` cd
utilisateur = |nom:Alice;age:20;ville:Nice|
```

Accéder à une valeur avec sa clé :

``` cd
print(utilisateur["nom"])
print(utilisateur["age"])
```

Les clés sont actuellement lues comme du texte. Pour éviter les
ambiguïtés, utiliser des clés simples sans `;` ni `:`.

## 7. Conditions

La forme prise en charge est :

``` cd
if[condition]
[
    # instructions si la condition est vraie
]
else [
    # instructions sinon
]
```

Exemple :

``` cd
age = 20

if[age >= 18]
[
    print("Majeur")
]
else [
    print("Mineur")
]
```

Le bloc `[` de la branche `if` doit être sur la ligne qui suit
`if[condition]`. Le bloc `else` peut être écrit `else [` sur une ligne,
comme dans l'exemple.

Les conditions acceptent les comparaisons et les opérateurs logiques
présentés plus haut.

## 8. Boucle repeat

Syntaxe :

``` cd
repeat i debut fin [
    # instructions répétées
]
```

La borne de fin est **incluse**. La variable de boucle reçoit
successivement les valeurs de `debut` à `fin`.

Exemple :

``` cd
repeat i 1 5 [
    print(i)
]
```

Affiche les nombres de 1 à 5.

Les bornes sont converties en entiers. Si la borne de départ est
supérieure à la borne de fin, le corps n'est pas exécuté.

## 9. Boucle while

Syntaxe :

``` cd
while condition [
    # instructions tant que la condition est vraie
]
```

Exemple :

``` cd
compteur = 0

while compteur < 3 [
    print(compteur)
    compteur = compteur + 1
]
```

La condition est réévaluée avant chaque passage dans la boucle.

L'interpréteur possède une limite de 10 000 étapes d'exécution par
script afin de limiter les boucles infinies. Si cette limite est
dépassée, une erreur est signalée.

## 10. Fonctions

Déclarer une fonction avec son nom, ses paramètres et un bloc :

``` cd
addition(a, b) [
    resultat = a + b
    return resultat
]
```

Appeler la fonction dans une expression :

``` cd
total = addition(10, 20)
print(total)
```

Règles actuelles : - le nom de fonction commence par une lettre ou `_`
; - les paramètres sont séparés par des virgules ; - le nombre
d'arguments à l'appel doit correspondre au nombre de paramètres ; - une
fonction doit contenir une instruction `return` ; - `return` est
utilisable uniquement dans une fonction ; - les variables locales d'une
fonction sont séparées des variables globales ; - une fonction renvoie
la valeur indiquée après `return`.

Exemple avec une condition :

``` cd
est_majeur(age) [
    if[age >= 18]
    [
        return "oui"
    ]
    else [
        return "non"
    ]
]

reponse = est_majeur(20)
print(reponse)
```

Le contrôle actuel vérifie la présence d'une ligne `return` dans le
corps de la fonction lors de sa déclaration. Pour garantir qu'un appel
renvoie effectivement une valeur, prévoir un `return` sur chaque chemin
d'exécution possible.

## 11. Afficher des informations

La fonction `print(...)` affiche les valeurs dans la sortie de l'éditeur
ou dans le terminal :

``` cd
nom = "Clement"
print("Bonjour", nom)
```

Dans un script exécuté avec `run`, la sortie est envoyée au terminal.
Depuis Clem Editor, elle apparaît dans le panneau de sortie en bas de la
fenêtre.

## 12. Exécuter les commandes de Clem Terminal

Une ligne qui n'est pas reconnue comme une instruction du langage est
interprétée comme une commande Clem Terminal.

Exemple :

``` cd
profil = "Clem"

cresce profil
gen_image profil "prompts.txt"
```

Les commandes disponibles dépendent de celles enregistrées dans
`main.py`. Dans la version actuelle, on retrouve notamment :

  Commande      Rôle
  ------------- -----------------------------------------
  `cinit`       Initialisation Chrome
  `copen`       Ouverture / gestion Chrome
  `cresce`      Ouvre Google Flow avec un profil Chrome
  `cproject`    Enregistre le projet Flow du profil
  `gen_image`   Lance la génération d'images
  `gen_video`   Lance la génération vidéo
  `save_img`    Sauvegarde les images
  `delflow`     Supprime les médias Flow

Consulter `help` dans Clem Terminal pour la liste et les usages exacts
des commandes disponibles.

Les arguments d'une commande sont découpés comme une ligne de commande
classique. Pour les chemins ou textes contenant des espaces, utiliser
des guillemets :

``` cd
gen_video profil "image de départ.png" "Un personnage dit bonjour"
```

## 13. Exemple complet

``` cd
# Exemple de script d'automatisation

profil = "Clem"
prompts = |prompt1.txt,prompt2.txt,prompt3.txt|
configuration = |format:9:16;sorties:3;mode:Image|

afficher_message(texte) [
    print("INFO :", texte)
    return true
]

afficher_message("Début de l'automatisation")

cresce profil

repeat i 0 2 [
    print("Traitement du prompt", i)
    gen_image profil prompts[i]
]

afficher_message("Script terminé")
```

Cet exemple illustre la syntaxe du langage. Les commandes externes
nécessitent naturellement un profil Chrome, un projet Flow et les
fichiers indiqués correctement configurés.

------------------------------------------------------------------------

## 14. Référence rapide

  Élément                     Syntaxe
  --------------------------- -----------------------------------
  Commentaire                 `# commentaire`
  Variable                    `nom = valeur`
  Tableau                     `nom = \|a,b,c\|`
  Dictionnaire                `nom = \|cle:val;cle:val\|`
  Lire un élément             `tableau[0]`
  Modifier un élément         `tableau[0] = valeur`
  Condition                   `if[condition]` puis bloc `[...]`
  Sinon                       `else [` puis bloc `[...]`
  Boucle bornée               `repeat i debut fin [`
  Boucle conditionnelle       `while condition [`
  Fonction                    `nom(arg1, arg2) [`
  Retour                      `return valeur`
  Affichage                   `print(valeur)`
  Exécution d'un script       `run fichier.cd`
  Ouvrir l'éditeur            `cedit fichier.cd`
  Exécuter depuis l'éditeur   `F5`

## 15. Limites connues de cette première version

-   Pas encore de boucle `break` ou `continue`.
-   Pas encore d'instruction `elif`.
-   Pas encore de syntaxe d'import de modules.
-   Pas encore de classes ni de programmation orientée objet.
-   Les fonctions utilisent des variables locales, mais les structures
    de portée avancées ne sont pas disponibles.
-   Les valeurs booléennes sont à écrire selon les expressions Python
    reconnues (`True` et `False`) dans cette version ; les mots
    minuscules `true` et `false` sont colorés par l'éditeur mais ne sont
    pas encore convertis par l'interpréteur.
-   La gestion des erreurs ne fournit pas encore systématiquement le
    numéro exact de ligne.
-   Les tableaux et dictionnaires utilisent une syntaxe compacte :
    éviter les séparateurs `,`, `;` et `:` dans les valeurs non
    protégées.

**Conseil :** commencer par tester les petits exemples de chaque section
avant de construire un script d'automatisation complet.
