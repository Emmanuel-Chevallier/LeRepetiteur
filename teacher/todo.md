Je veux écrire un logiciel pédagogique utilisant l'IA (les modèles gemini) pour poser des interrogations de cours de façon entièrement automatisée et personnalisée. Le Logiciel peut se décomposer en 3 parties. Les parties I) et II) sont interconnectées dans la mesure ou elle produisent et nécessitent des données fournis par l'autre partie. La partie III) fait appel aux données des parties I) et II) mais ne produit pas de données. Toutes les données nécessaires seront stockées sur un serveur (python). L'interface prendre la forme d'une page web accessible à l'enseignant et au étudiants par un login et un mot de passe.  

-------------------------------------------------------------------------------
Données stockés sur le serveur:

-liste d'étudiants (identifiés par un numéro), qui doit pouvoir être mise à jour
-liste de cours, qui doit également pouvoir être mise à jour

Pour chaque cours, on devra pouvoir inscrire des étudiants depuis la liste d'étudiants.

Pour chaque étudiant, un dossier sera créer contenant
-1 fichier pour chaque scans de ses questionnaires
-1 fichier pour la transcription et la correction ia de chaque questionnaire scanné


--------------------------------------------------------------------
I) Génération des questions et de leurs bonnes réponses

Données d'entrée:
-fichier latex du cours
-partie du latex vue dans la séance de cours précédente
-historique des question précédentes par étudiants et des corrections produites par la partie II)
-prompt d'instruction à l'IA indiquant le style de questions à poser

Sortie:
-Questionnaire personnalisé par étudiant avec 50% des questions commune à tout les étudiants qui portent sur la dernière
partie vue en cours, et 50% sur les difficultés identifiées dans l'historique de l'étudiant.
-Un barême avec le nombre de points par question (20 au total)
-mise en forme du questionnaire sur un feuille A4 avec le numéro identifiant l'étudiant (pas son nom) et une suite de
-question
-encadré prévu pour la réponse
Les le tout sera stockés sur le serveur.

II) Correction des copies des étudiants

Entrée:
-Les scans des copies

Sorties (stockées sur le serveur)
-transcription des scans en latex.
-corrections des transcriptions latex + note sur 20
-génération d'un document de synthèse évaluant la réussite globale de l'évaluation

III) chatbot personnalisés pour chaque étudiant

Contexte:
-fichier latex du cours
-historique des questionnaires
-historique des documents de synthèse évaluant la réussite globale
-historique des réponses de l'étudiant

----------------------------------------------------------------------------------------------------
Interface.

1.Version enseignant (accessible avec un mot de passe enseignant)
-bouton nouveau cours: demande le fichier latex du cours et créer le cours
-quand on selectionne un cours on doit pouvoir:
-indiquer la ligne du fichier latex correspondant à la fin de la dernière séance (et voir les numéros de lignes des séances précédantes)
-ajouter/retirer des étudiants
-indiquer un prompt pour guider les questionnaires
-lancer la génération des questionnaires pour touts les étudiants inscrits au cours
-lancer la génération d'un questionnaire pour un étudiant en particulier.
-voir les notes moyennes des questionnaires précédants et les synthèses correspondantes rédigées par l'ia
-uploader les scan de questionnaires
-lancer les corrections automatiques pour un ensemble de scan sélectionnés

1.Version étudiant
Chaque étudiant doit pouvoir acceder à sa propre page. Les enseignants doivent pouvoir la voir aussi.
L'étudiant doit pouvoir sélectionner un cours, voir les scans de ses questionnaires, leurs transcriptions et leurs corrections.

----------------------------------------------------------------------------------------------------------

Comment le faire:
1. créer un document décrivant comment les données seront stockées (un format lisible par les humains type CSV ou JSON)
2. Implementer I et II
3. Quand I. et II. fonctionnent, passer à III.


