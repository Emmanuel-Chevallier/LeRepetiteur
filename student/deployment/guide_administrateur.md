# 🦅 InterroPedago V3 - Guide Administrateur Système

**Objet :** Déploiement du module "Etudiant" sur serveur AlmaLinux 9.

Bonjour,

Ce document détaille les prérequis et les procédures pour déployer l'application **InterroPedago (Module Étudiant)**. C'est une application légère en **Python (FastAPI)** qui doit tourner sur le port **8002**.

Nous avons pré-packagé deux méthodes de déploiement (Docker ou Native) pour simplifier votre travail.

---

## 1. Options de Déploiement (au choix)

Tous les scripts mentionnés se trouvent dans le dossier `deployment/` une fois l'archive dézippée.

### 🐳 Option A : Docker (Recommandée)
L'application est "docker-ready". C'est la méthode la plus propre pour isoler les dépendances.

*   **Fichiers fournis :** `Dockerfile`, `docker-compose.yml`.
*   **Action requise :**
    1.  Définir la clé API (voir section Sécurité).
    2.  Lancer : `docker-compose up -d --build`

### 🐧 Option B : Service Natif (Systemd)
Si vous préférez une installation standard sur l'hôte.

*   **Fichier fourni :** `install_almalinux.sh`.
*   **Action requise :**
    1.  Lancer le script (en root/sudo) : `bash deployment/install_almalinux.sh`
    2.  Ce script installe Python 3.9+, crée un venv, configure un user `interropedago` et un service systemd.

---

## 2. Sécurité & Configuration

L'application nécessite une clé API Google Gemini pour fonctionner.

*   **Variable d'environnement :** `GEMINI_API_KEY`
*   **Configuration :**
    *   **Docker :** Ajoutez `GEMINI_API_KEY=votre_cle` dans le `docker-compose.yml` ou un fichier `.env`.
    *   **Systemd :** Le script d'installation a créé un placeholder dans `/etc/systemd/system/interropedago-student.service`. Merci de l'éditer pour y mettre la vraie clé.

---

## 3. Maintenance & Autonomie de l'Enseignant

L'enseignant (utilisateur) sera amené à mettre à jour le code (fichiers `.py` ou `.html`) via **SFTP**.

**⚠️ Problème :**
Pour que les modifications Python soient prises en compte, le service doit être redémarré.

**🙏 Demande Spécifique :**
Pour éviter de vous solliciter à chaque mise à jour mineure, nous vous serions reconnaissants d'accorder à l'utilisateur SSH de l'enseignant le droit de redémarrer ce service spécifique **sans mot de passe**.

*Exemple de ligne `sudoers` souhaitée :*
```bash
# Pour Option Systemd
nom_utilisateur ALL=(root) NOPASSWD: /usr/bin/systemctl restart interropedago-student

# Pour Option Docker
nom_utilisateur ALL=(root) NOPASSWD: /usr/bin/docker-compose restart
```

Merci.
