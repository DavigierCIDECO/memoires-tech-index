# 📂 Explorateur de Fichiers Windows - Mode d'emploi

## 🎉 Nouvelle Fonctionnalité !

Vous pouvez maintenant utiliser l'**explorateur Windows natif** pour sélectionner vos dossiers et fichiers à indexer, au lieu de taper les chemins manuellement.

---

## 📁 Sélection de Dossier

### Comment accéder
1. Lancez l'interface web : `streamlit run app.py`
2. Allez dans l'onglet **"📥 Indexation"**
3. Sélectionnez le mode **"📁 Dossier complet"**
4. Cliquez sur le bouton **"📂 Parcourir..."**

### Fonctionnement
- Une fenêtre Windows s'ouvre automatiquement
- Naviguez visuellement dans vos dossiers
- Sélectionnez le dossier contenant vos MTs
- Cliquez sur **"Sélectionner le dossier"**
- Le chemin est automatiquement rempli dans le champ texte

### Démarrage intelligent
- Si vous avez configuré `LOCAL_DOCS_PATH` dans votre `.env`
- L'explorateur s'ouvre directement dans ce dossier

---

## 📄 Sélection de Fichiers

### Comment accéder
1. Lancez l'interface web : `streamlit run app.py`
2. Allez dans l'onglet **"📥 Indexation"**
3. Sélectionnez le mode **"📄 Fichier(s) individuel(s)"**
4. Cliquez sur le bouton **"📂 Parcourir..."**

### Fonctionnement
- Une fenêtre Windows s'ouvre avec filtrage automatique
- Seuls les formats supportés sont affichés par défaut :
  - `.docx` (Word)
  - `.pdf` (PDF)
  - `.doc` (Word ancien)
  - `.docm` (Word avec macros)

### Sélection Multiple

**Sélectionner plusieurs fichiers en même temps** :

- **`Ctrl + clic`** : Ajouter/retirer un fichier de la sélection
  ```
  Fichier1.docx [clic]
  Fichier3.docx [Ctrl+clic]
  Fichier5.docx [Ctrl+clic]
  → 3 fichiers sélectionnés
  ```

- **`Shift + clic`** : Sélectionner une plage
  ```
  Fichier1.docx [clic]
  Fichier5.docx [Shift+clic]
  → Fichiers 1, 2, 3, 4, 5 sélectionnés
  ```

- **Combinaison** :
  ```
  Fichier1.docx [clic]
  Fichier3.docx [Shift+clic]  → 1, 2, 3 sélectionnés
  Fichier5.docx [Ctrl+clic]   → Ajouter 5
  Fichier7.docx [Ctrl+clic]   → Ajouter 7
  → Fichiers 1, 2, 3, 5, 7 sélectionnés
  ```

### Validation
- Cliquez sur **"Ouvrir"** pour valider la sélection
- Les chemins sont automatiquement remplis dans la zone de texte
- Vous pouvez encore modifier manuellement si besoin

---

## 🔄 Mode Hybride

**Vous pouvez combiner les deux approches** :

1. Utilisez **"📂 Parcourir..."** pour sélectionner rapidement
2. Modifiez manuellement le chemin dans le champ texte si besoin
3. Ajoutez des chemins supplémentaires ligne par ligne

### Exemple
```
# Parcourir sélectionne :
C:\MTs\2026\Janvier\Doc1.docx
C:\MTs\2026\Janvier\Doc2.docx

# Vous ajoutez manuellement :
C:\MTs\2026\Janvier\Doc3.docx
C:\Autres\DocumentSpecial.pdf

→ 4 fichiers seront indexés
```

---

## ⚙️ Configuration

### Dossier de démarrage

Pour que l'explorateur s'ouvre toujours dans votre dossier de MTs :

1. Ouvrez votre fichier `.env`
2. Ajoutez ou modifiez :
   ```
   LOCAL_DOCS_PATH=C:\Users\David\Documents\MTs
   ```
3. Sauvegardez
4. L'explorateur s'ouvrira dans ce dossier par défaut

### Formats de fichiers

Les types suivants sont filtrés automatiquement :
- Documents supportés (tous formats)
- Word Documents (.docx, .doc, .docm)
- PDF Documents (.pdf)
- Tous les fichiers (si vous voulez voir tout)

**Changement de filtre** : En bas de la fenêtre Windows, vous pouvez changer le filtre pour voir d'autres types.

---

## 💡 Conseils d'utilisation

### Pour indexer un nouveau projet
1. Mode **"📁 Dossier complet"**
2. **"📂 Parcourir..."**
3. Naviguer vers `C:\MTs\Nouveau_Projet`
4. Sélectionner le dossier
5. **"Lancer l'indexation"**

### Pour indexer quelques documents spécifiques
1. Mode **"📄 Fichier(s) individuel(s)"**
2. **"📂 Parcourir..."**
3. `Ctrl+clic` sur les fichiers voulus
4. **"Ouvrir"**
5. **"Lancer l'indexation"**

### Pour l'indexation hebdomadaire
1. Mode **"🔄 Utiliser le chemin par défaut"**
   - Pas besoin de parcourir !
   - Utilise automatiquement `LOCAL_DOCS_PATH`
2. **"Lancer l'indexation"**

---

## 🐛 Résolution de problèmes

### L'explorateur ne s'ouvre pas
- **Cause** : tkinter n'est pas installé
- **Solution** :
  ```bash
  pip install tk
  ```

### La fenêtre reste bloquée
- **Cause** : Conflit avec Streamlit
- **Solution** :
  - Fermez la fenêtre de l'explorateur
  - Rechargez la page (`Ctrl+R`)
  - Réessayez

### Les fichiers ne s'affichent pas
- **Cause** : Mauvais filtre de type de fichier
- **Solution** :
  - En bas de la fenêtre, changez le filtre vers "Tous les fichiers"
  - Ou vérifiez que vos fichiers ont bien l'extension .docx, .pdf, etc.

### Le chemin n'apparaît pas après sélection
- **Cause** : L'utilisateur a annulé la sélection
- **Solution** :
  - Recliquez sur "📂 Parcourir..."
  - Sélectionnez un dossier/fichier
  - Validez avec "Sélectionner" ou "Ouvrir"

---

## 🎯 Avantages

✅ **Plus rapide** : Plus besoin de taper les chemins
✅ **Plus sûr** : Pas d'erreur de typo dans les chemins
✅ **Plus intuitif** : Navigation visuelle familière
✅ **Sélection multiple** : Indexer plusieurs fichiers en un clic
✅ **Filtrage automatique** : Voir uniquement les formats supportés

---

## 📚 Ressources

- **Guide complet** : `GUIDE_INTERFACE_WEB.md`
- **Nouvelles fonctionnalités** : `NOUVELLES_FONCTIONNALITES_V2.md`
- **README principal** : `README.md`

---

**Profitez de cette nouvelle fonctionnalité pour gagner du temps !** ⏱️
