"""Système d'apprentissage pour améliorer les prompts d'indexation."""
import json
import logging
from typing import Dict, List
from datetime import datetime
from collections import Counter

from anthropic import Anthropic
import config

logger = logging.getLogger(__name__)


class LearningSystem:
    """Système qui apprend des enrichissements manuels pour améliorer l'indexation."""

    def __init__(self):
        """Initialise le système d'apprentissage."""
        if not config.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY non définie. "
                "Créez un fichier .env avec votre clé API."
            )

        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.storage = config.get_storage()

    def load_enrichments_history(self) -> List[Dict]:
        """Charge l'historique des enrichissements.

        Returns:
            Liste des enrichissements
        """
        if not self.storage.json_exists("enrichments_history"):
            return []

        history = self.storage.read_json("enrichments_history")
        if history is None:
            return []

        return history.get("enrichments", [])

    def analyze_enrichments(self) -> Dict:
        """Analyse les enrichissements pour détecter des patterns.

        Returns:
            Dictionnaire avec insights et patterns détectés
        """
        enrichments = self.load_enrichments_history()

        if not enrichments:
            return {
                "total_enrichments": 0,
                "patterns": [],
                "suggestions": []
            }

        # Analyser les champs les plus modifiés
        field_counter = Counter()
        action_counter = Counter()
        added_values = {}
        removed_values = {}

        for enrich in enrichments:
            for modif in enrich.get("modifications", {}).get("modifications", []):
                action = modif.get("action")
                champ = modif.get("champ")
                valeur = modif.get("valeur")

                field_counter[champ] += 1
                action_counter[f"{action}_{champ}"] += 1

                # Tracker les valeurs ajoutées/retirées
                if action == "AJOUTER":
                    if champ not in added_values:
                        added_values[champ] = []
                    if isinstance(valeur, list):
                        added_values[champ].extend(valeur)
                    else:
                        added_values[champ].append(valeur)

                elif action == "RETIRER":
                    if champ not in removed_values:
                        removed_values[champ] = []
                    if isinstance(valeur, list):
                        removed_values[champ].extend(valeur)
                    else:
                        removed_values[champ].append(valeur)

        # Identifier les patterns significatifs
        patterns = []

        # Pattern 1: Champs fréquemment modifiés (possibles oublis systématiques)
        for champ, count in field_counter.most_common(5):
            if count >= 3:  # Au moins 3 modifications
                patterns.append({
                    "type": "champ_fréquent",
                    "champ": champ,
                    "count": count,
                    "description": f"Le champ '{champ}' est modifié dans {count} documents - possible oubli systématique"
                })

        # Pattern 2: Valeurs fréquemment ajoutées (non détectées par l'IA)
        for champ, values in added_values.items():
            # Filtrer les valeurs non-hashables (dicts, lists) pour Counter
            hashable_values = [v for v in values if isinstance(v, (str, int, float, bool, type(None)))]
            if not hashable_values:
                continue
            value_counts = Counter(hashable_values)
            for value, count in value_counts.most_common(3):
                if count >= 2:  # Ajouté au moins 2 fois
                    patterns.append({
                        "type": "valeur_ajoutée_fréquente",
                        "champ": champ,
                        "valeur": value,
                        "count": count,
                        "description": f"'{value}' ajouté {count} fois dans {champ} - non détecté automatiquement"
                    })

        # Pattern 3: Valeurs fréquemment retirées (faux positifs de l'IA)
        for champ, values in removed_values.items():
            # Filtrer les valeurs non-hashables (dicts, lists) pour Counter
            hashable_values = [v for v in values if isinstance(v, (str, int, float, bool, type(None)))]
            if not hashable_values:
                continue
            value_counts = Counter(hashable_values)
            for value, count in value_counts.most_common(3):
                if count >= 2:  # Retiré au moins 2 fois
                    patterns.append({
                        "type": "valeur_retirée_fréquente",
                        "champ": champ,
                        "valeur": value,
                        "count": count,
                        "description": f"'{value}' retiré {count} fois de {champ} - possiblement un faux positif"
                    })

        return {
            "total_enrichments": len(enrichments),
            "analyzed_at": datetime.now().isoformat(),
            "patterns": patterns,
            "field_stats": dict(field_counter),
            "action_stats": dict(action_counter)
        }

    def generate_prompt_improvements(self, insights: Dict) -> Dict:
        """Génère des suggestions d'amélioration des prompts basées sur les insights.

        Args:
            insights: Insights de l'analyse

        Returns:
            Dictionnaire avec suggestions d'amélioration
        """
        patterns = insights.get("patterns", [])

        if not patterns:
            return {
                "improvements": [],
                "generated_at": datetime.now().isoformat()
            }

        # Construire le contexte pour Claude
        patterns_text = "\n".join([
            f"- [{p['type']}] {p['description']}"
            for p in patterns
        ])

        # Charger les enrichissements récents pour exemples
        enrichments = self.load_enrichments_history()[-10:]  # 10 derniers
        examples_text = "\n\n".join([
            f"Document: {e.get('filename', 'Inconnu')}\n"
            f"Input utilisateur: {e.get('modifications', {}).get('original_input', 'N/A')}\n"
            f"Modifications: {e.get('modifications', {}).get('résumé_modifications', 'N/A')}"
            for e in enrichments
        ])

        prompt = f"""Tu es un expert en amélioration de prompts pour l'extraction d'information via IA.

CONTEXTE:
Un système d'indexation automatique de mémoires techniques utilise Claude pour extraire des métadonnées structurées.
Des utilisateurs enrichissent manuellement les résultats quand l'IA fait des erreurs ou oublie des informations.

PATTERNS DÉTECTÉS DANS LES ENRICHISSEMENTS MANUELS:
{patterns_text}

EXEMPLES D'ENRICHISSEMENTS RÉCENTS:
{examples_text}

TÂCHE:
Analyse ces patterns et propose des améliorations concrètes au prompt d'indexation pour réduire les erreurs.

Pour chaque amélioration, fournis:
1. Le type de problème détecté
2. Une suggestion concrète d'amélioration du prompt
3. Un exemple de formulation à ajouter/modifier dans le prompt

FORMAT DE RÉPONSE (JSON strict):
{{
  "improvements": [
    {{
      "probleme": "description du problème",
      "champ_concerné": "nom du champ",
      "suggestion": "suggestion d'amélioration concrète",
      "exemple_prompt": "exemple de texte à ajouter dans le prompt",
      "priorité": "haute|moyenne|basse"
    }}
  ],
  "résumé": "résumé global des améliorations proposées"
}}

IMPORTANT:
- Sois spécifique et actionable
- Propose des modifications de prompt qui peuvent être directement intégrées
- Priorise les améliorations ayant le plus d'impact
- Limite-toi aux 5 améliorations les plus importantes
"""

        try:
            message = self.client.messages.create(
                model=config.SUMMARY_MODEL,
                max_tokens=config.SUMMARY_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            # Parser le JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            improvements = json.loads(response_text)
            improvements["generated_at"] = datetime.now().isoformat()
            improvements["based_on_enrichments"] = insights["total_enrichments"]

            # Sauvegarder les suggestions
            self._save_improvements(improvements)

            return improvements

        except Exception as e:
            logger.error(f"Erreur lors de la génération des améliorations: {e}")
            return {
                "error": str(e),
                "improvements": [],
                "generated_at": datetime.now().isoformat()
            }

    def _save_improvements(self, improvements: Dict):
        """Sauvegarde les améliorations proposées.

        Args:
            improvements: Améliorations à sauvegarder
        """
        # Charger les améliorations existantes
        if self.storage.json_exists("prompt_improvements"):
            history = self.storage.read_json("prompt_improvements")
            if history is None:
                history = {"history": []}
        else:
            history = {"history": []}

        # Ajouter cette nouvelle génération
        history["history"].append(improvements)
        history["latest"] = improvements

        # Sauvegarder
        self.storage.write_json("prompt_improvements", history)

        logger.info("Améliorations sauvegardées")

    def get_latest_improvements(self) -> Dict:
        """Récupère les dernières améliorations proposées.

        Returns:
            Dernières améliorations ou dict vide
        """
        if not self.storage.json_exists("prompt_improvements"):
            return {"improvements": []}

        history = self.storage.read_json("prompt_improvements")
        if history is None:
            return {"improvements": []}

        return history.get("latest", {"improvements": []})

    def apply_improvement_to_prompt(
        self, improvement: Dict, current_prompt: str
    ) -> str:
        """Applique une amélioration au prompt actuel.

        Args:
            improvement: Amélioration à appliquer
            current_prompt: Prompt actuel

        Returns:
            Prompt amélioré
        """
        # Pour l'instant, retourne le prompt avec un commentaire d'amélioration
        # Dans une implémentation future, cela modifierait directement le prompt dans indexer.py

        exemple_prompt = improvement.get("exemple_prompt", "")
        champ = improvement.get("champ_concerné", "")

        # Trouver où insérer l'amélioration dans le prompt
        # (logique à implémenter selon la structure du prompt)

        improved_prompt = current_prompt + f"\n\n# AMÉLIORATION AUTOMATIQUE pour {champ}:\n{exemple_prompt}"

        return improved_prompt

    def validate_improvement(self, index: int, validated: bool, modified_text: str = None) -> bool:
        """Valide ou rejette une amélioration.

        Args:
            index: Index de l'amélioration (0-based)
            validated: True pour valider, False pour rejeter
            modified_text: Texte modifié par l'utilisateur (optionnel)

        Returns:
            True si succès, False sinon
        """
        if not self.storage.json_exists("prompt_improvements"):
            return False

        history = self.storage.read_json("prompt_improvements")
        if history is None:
            return False

        latest = history.get("latest", {})
        improvements = latest.get("improvements", [])

        if index < 0 or index >= len(improvements):
            return False

        # Ajouter le statut de validation
        improvements[index]["validated"] = validated
        improvements[index]["validated_at"] = datetime.now().isoformat()
        if modified_text is not None:
            improvements[index]["exemple_prompt_modified"] = modified_text

        # Sauvegarder
        history["latest"]["improvements"] = improvements
        self.storage.write_json("prompt_improvements", history)

        return True

    def get_pending_improvements(self) -> List[Dict]:
        """Récupère les améliorations en attente de validation.

        Returns:
            Liste des améliorations non encore validées/rejetées
        """
        latest = self.get_latest_improvements()
        return [
            {"index": i, **imp}
            for i, imp in enumerate(latest.get("improvements", []))
            if "validated" not in imp
        ]

    def get_validated_improvements(self) -> List[Dict]:
        """Récupère les améliorations validées (non encore appliquées).

        Returns:
            Liste des améliorations validées
        """
        latest = self.get_latest_improvements()
        return [
            {"index": i, **imp}
            for i, imp in enumerate(latest.get("improvements", []))
            if imp.get("validated") == True and not imp.get("committed")
        ]

    def commit_improvements(self) -> Dict:
        """Applique les améliorations validées.

        Sauvegarde les règles apprises dans un fichier qui sera utilisé
        par l'indexeur pour améliorer l'analyse.

        Returns:
            Résultat du commit
        """
        validated = self.get_validated_improvements()
        if not validated:
            return {"success": False, "message": "Aucune amélioration validée à appliquer"}

        # Charger les règles existantes
        if self.storage.json_exists("learned_rules"):
            rules = self.storage.read_json("learned_rules")
            if rules is None:
                rules = {"rules": [], "applied_at": []}
        else:
            rules = {"rules": [], "applied_at": []}

        # Ajouter les nouvelles règles
        committed_count = 0
        for imp in validated:
            rule = {
                "champ": imp.get("champ_concerné"),
                "probleme": imp.get("probleme"),
                "suggestion": imp.get("suggestion"),
                "prompt_addition": imp.get("exemple_prompt_modified") or imp.get("exemple_prompt"),
                "priorité": imp.get("priorité"),
                "committed_at": datetime.now().isoformat()
            }
            rules["rules"].append(rule)
            committed_count += 1

        rules["last_commit"] = datetime.now().isoformat()
        rules["applied_at"].append({
            "timestamp": datetime.now().isoformat(),
            "count": committed_count
        })

        # Sauvegarder les règles
        self.storage.write_json("learned_rules", rules)

        # Marquer les améliorations comme committées
        history = self.storage.read_json("prompt_improvements")

        for imp in validated:
            idx = imp["index"]
            history["latest"]["improvements"][idx]["committed"] = True
            history["latest"]["improvements"][idx]["committed_at"] = datetime.now().isoformat()

        self.storage.write_json("prompt_improvements", history)

        logger.info(f"{committed_count} améliorations appliquées")

        return {
            "success": True,
            "committed_count": committed_count,
            "message": f"{committed_count} amélioration(s) appliquée(s)"
        }

    def get_learned_rules(self) -> List[Dict]:
        """Récupère les règles apprises et appliquées.

        Returns:
            Liste des règles
        """
        if not self.storage.json_exists("learned_rules"):
            return []

        rules = self.storage.read_json("learned_rules")
        if rules is None:
            return []

        return rules.get("rules", [])

    def run_learning_cycle(self) -> Dict:
        """Lance un cycle complet d'apprentissage.

        Returns:
            Résultat du cycle d'apprentissage
        """
        logger.info("Démarrage du cycle d'apprentissage...")

        # Étape 1: Analyser les enrichissements
        insights = self.analyze_enrichments()
        logger.info(f"Analyse terminée: {insights['total_enrichments']} enrichissements analysés")

        # Sauvegarder les insights
        self.storage.write_json("learning_insights", insights)

        # Étape 2: Générer des améliorations
        if insights["total_enrichments"] > 0:
            improvements = self.generate_prompt_improvements(insights)
            logger.info(f"Généré {len(improvements.get('improvements', []))} améliorations")
        else:
            improvements = {"improvements": [], "message": "Pas assez d'enrichissements pour apprendre"}

        return {
            "success": True,
            "insights": insights,
            "improvements": improvements,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """Point d'entrée pour lancer un cycle d'apprentissage manuellement."""
    import sys

    logging.basicConfig(level=logging.INFO)

    learning_system = LearningSystem()
    result = learning_system.run_learning_cycle()

    print("\n" + "="*80)
    print("CYCLE D'APPRENTISSAGE TERMINÉ")
    print("="*80)

    print(f"\nEnrichissements analysés: {result['insights']['total_enrichments']}")
    print(f"Patterns détectés: {len(result['insights']['patterns'])}")

    if result['improvements'].get('improvements'):
        print(f"\nAméliorations proposées: {len(result['improvements']['improvements'])}")
        print("\nRésumé:", result['improvements'].get('résumé', 'N/A'))

        print("\nDétail des améliorations:")
        for i, imp in enumerate(result['improvements']['improvements'], 1):
            print(f"\n{i}. [{imp.get('priorité', 'N/A').upper()}] {imp.get('probleme', 'N/A')}")
            print(f"   Champ: {imp.get('champ_concerné', 'N/A')}")
            print(f"   Suggestion: {imp.get('suggestion', 'N/A')}")
    else:
        print("\nAucune amélioration générée (pas assez de données)")


if __name__ == "__main__":
    main()
