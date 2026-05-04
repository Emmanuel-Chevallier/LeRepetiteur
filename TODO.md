# À Faire (TODO)

## Gestion des Quizz
- [ ] **Gestion de la numérotation des quiz** : Ajouter une fonctionnalité pour pouvoir supprimer proprement des données d'un quiz qui n'aurait finalement pas été donné en pratique. Le but est d'éviter d'avoir un trou ou un numéro de quiz intermédiaire manquant dans l'interface et les dossiers.

## Intégration AMeTICE (Moodle AMU)

Objectif : remplacer l'interface étudiante custom par AMeTICE pour la distribution des corrections.

### Sans autorisation admin (faisable immédiatement)

- [ ] **Export HTML self-contained** : Générer un fichier HTML autonome (login JS côté client, données JSON embarquées, rendu Markdown+MathJax via CDN). L'enseignant uploade manuellement dans AMeTICE comme ressource "Fichier" (affichage "Intégré"). Limite : toutes les données sont dans le source HTML (filtrage par login côté client uniquement).

- [ ] **Export ZIP individuel (Devoir Moodle)** : Générer un ZIP avec un fichier HTML de correction par étudiant, compatible avec l'upload en masse de "fichiers de feedback" dans une activité Devoir Moodle. Chaque étudiant ne voit que sa propre correction. Nécessite le mapping des identifiants Moodle (ou renommage manuel des dossiers).

- [ ] **Export historique étudiant** : Bouton côté étudiant pour télécharger un fichier Markdown contenant tout son historique (questions, réponses, scores, feedback), optimisé pour être donné à un LLM externe (ChatGPT, Gemini, Claude).

### Avec autorisation admin CIPE (à demander)

- [ ] **API REST Moodle — Push des notes** : Utiliser `mod_assign_save_grade` pour pousser automatiquement les notes dans le carnet de notes AMeTICE. Nécessite : activation des Web Services REST + token API enseignant.

- [ ] **API REST Moodle — Feedback individuel** : Attacher automatiquement les fichiers de correction en feedback individuel via l'API. Nécessite : mêmes prérequis + mapping ID étudiant ↔ ID Moodle.

- [ ] **LTI 1.3 — Outil externe** : Enregistrer Le Répétiteur comme outil externe LTI dans AMeTICE. L'interface étudiante s'affiche en iframe dans Moodle, les scores sont renvoyés au gradebook. Nécessite : serveur HTTPS public + enregistrement LTI par le CIPE + OAuth2/JWT.

- [ ] **Déploiement automatique complet** : Bouton "🚀 Déployer → AMeTICE" qui pousse automatiquement les corrections cours par cours, étudiant par étudiant, sans intervention manuelle. Nécessite : token API + mapping étudiants. Le code de collecte des données est le même que pour l'export manuel.

### Prochaine étape recommandée
Contacter le CIPE (support AMeTICE via FacilitAMU) pour :
1. Demander si les Web Services REST sont activés
2. Demander un token API avec les droits enseignant
3. Obtenir la procédure pour récupérer les IDs Moodle des étudiants inscrits
