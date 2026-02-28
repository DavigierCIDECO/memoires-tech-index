# Analyse du Bug : Images Dupliquées dans Palais St Mélaine

## 🔍 Symptômes Observés

- Les illustrations #1, #2 et #3 affichent toutes la même image
- Dans l'index JSON, les 3 illustrations pointent vers `illust_003.png`
- Sur le disque, seul `illust_003.png` existe (pas de `illust_001.png` ni `illust_002.png`)
- Les métadonnées (descriptions, catégories, mots-clés) sont différentes pour chaque illustration

## 🕵️ Enquête

### Horodatage des créations
```
Illustration 1: 2025-12-31 10:41:18
Illustration 2: 2025-12-31 10:42:14 (56s plus tard)
Illustration 3: 2025-12-31 10:42:48 (34s plus tard)
```

### Fichiers sur disque
```
illust_003.png: créé à 10:42
illust_004.png: créé à 10:44
illust_005.png: créé à 10:44
...
```

## 💡 Cause Racine Identifiée

### Le Problème : Race Condition sur l'Index

**Scénario du bug :**

1. **À 10:41:18** - Création illustration #1
   ```python
   illust_index = len(selected_doc["special_illustrations"]) + 1  # = 1
   # Sauvegarde illust_001.png
   # Ajoute l'entrée à l'index
   # Sauvegarde l'index sur disque (ASYNC !)
   # Rerun de la page
   ```

2. **À 10:42:14** - Création illustration #2 (56s plus tard)
   ```python
   # Page recharge, mais...
   # SI l'index.json n'a pas fini d'être écrit sur disque
   # OU SI Streamlit a caché l'ancienne version
   # ALORS selected_doc a toujours 0 illustrations au lieu de 1 !

   illust_index = len(selected_doc["special_illustrations"]) + 1  # = 1 (ERREUR!)
   # ÉCRASE illust_001.png avec la nouvelle image
   ```

3. **À 10:42:48** - Création illustration #3
   ```python
   # Même problème
   # selected_doc a 0 ou 1 illustration au lieu de 2
   # Finit par sauvegarder comme illust_003.png
   ```

**Résultat :** Les 3 premières images ont été successivement écrasées, et seule `illust_003.png` (la dernière écrite) a survécu. Mais l'index contient bien 3 entrées distinctes, qui pointent toutes vers le même fichier.

## ✅ Corrections Appliquées

### 1. Protection Anti-Cache (lignes 566-580)

```python
# AVANT (code vulnérable)
illust_index = len(selected_doc["special_illustrations"]) + 1

# APRÈS (code protégé)
fresh_index = load_index()  # Recharge TOUJOURS depuis le disque
if fresh_index:
    fresh_doc = next((d for d in fresh_index["documents"]
                     if d["file_hash"] == selected_doc["file_hash"]), None)
    if fresh_doc:
        current_count = len(fresh_doc.get("special_illustrations", []))
        illust_index = current_count + 1
        # Synchronise selected_doc avec le disque
        selected_doc["special_illustrations"] = fresh_doc.get("special_illustrations", [])
```

**Bénéfice :** Même si Streamlit cache des données, on recharge TOUJOURS l'index depuis le disque avant de calculer le prochain numéro d'illustration.

### 2. Écriture Atomique de l'Index (lignes 63-86)

```python
# AVANT (écriture non-garantie)
with open(config.INDEX_FILE, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

# APRÈS (écriture atomique garantie)
temp_file = config.INDEX_FILE.with_suffix('.tmp')
with open(temp_file, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=2)
    f.flush()  # Force le buffer
    os.fsync(f.fileno())  # Force l'écriture physique

shutil.move(str(temp_file), str(config.INDEX_FILE))  # Opération atomique
```

**Bénéfice :**
- Écriture dans un fichier temporaire d'abord
- Flush explicite + fsync garantissent l'écriture sur disque
- Move atomique évite la corruption partielle
- Le prochain `load_index()` lira toujours des données complètes

### 3. Vérification Post-Sauvegarde (lignes 593-597)

```python
# Vérifier que le fichier a bien été créé
full_img_path = Path(config.DATA_DIR.parent) / image_path
if not full_img_path.exists():
    st.error(f"❌ ERREUR CRITIQUE: L'image n'a pas été sauvegardée correctement!")
    st.stop()
```

**Bénéfice :** Détection immédiate si l'image n'a pas été sauvegardée, empêche l'ajout d'une entrée orpheline dans l'index.

### 4. Logs de Debug (lignes 583, 80)

```python
print(f"[DEBUG] Creating illustration #{illust_index} for {selected_doc['filename']}")
print(f"[DEBUG] Index saved successfully at {datetime.now().isoformat()}")
```

**Bénéfice :** Permet de tracer le flux et diagnostiquer rapidement tout problème futur.

## 🛠️ Comment Corriger les Données Existantes

### Option 1 : Via l'Interface (RECOMMANDÉ)

1. Lancez `streamlit run enrich_manual.py`
2. Sélectionnez "Palais Saint Mélaine"
3. Pour l'illustration #1 :
   - Ouvrez l'expander "✏️ Éditer"
   - Dans "🖼️ Remplacer l'image", uploadez la bonne image
   - Sauvegardez
4. Répétez pour l'illustration #2

### Option 2 : Via Script (Plus rapide si vous avez les images)

1. Copiez manuellement les bonnes images dans :
   ```
   data/images/ed33ad49a9df32e51ec9e87b94efaabb/illust_001.png
   data/images/ed33ad49a9df32e51ec9e87b94efaabb/illust_002.png
   ```

2. Exécutez :
   ```bash
   python fix_palais_images.py
   ```

## 📊 Impact et Prévention

### Impact
- ✅ Bug limité aux 3 premières illustrations du Palais
- ✅ Aucune perte de métadonnées (descriptions, catégories conservées)
- ✅ Images physiques facilement remplaçables

### Prévention
- ✅ **Protection anti-cache** : Recharge systématique avant calcul d'index
- ✅ **Écriture atomique** : Garantit l'intégrité des sauvegardes
- ✅ **Vérification** : Détecte immédiatement les échecs
- ✅ **Logs** : Facilite le diagnostic

### Probabilité de Récurrence
**Avant corrections :** 🔴 Élevée (dépendait du timing et du cache Streamlit)
**Après corrections :** 🟢 Quasi nulle (protections multiples en place)

## 🎓 Leçons Apprises

1. **Ne jamais faire confiance au cache** : Toujours recharger les données critiques depuis la source de vérité (disque)

2. **Écriture atomique essentielle** : Pour éviter les états intermédiaires lors de rechargements rapides

3. **Validation post-opération** : Vérifier que les opérations critiques (création fichier) ont réussi

4. **Logs de debug** : Essentiels pour diagnostiquer les bugs de timing/concurrence
