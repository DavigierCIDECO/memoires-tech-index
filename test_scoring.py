"""Script de test pour voir le détail du scoring."""
import sys
from find_similar import SimilarityFinder

finder = SimilarityFinder()
results = finder.find_similar("plat carbone", is_file=False, max_results=5)

with open("test_results.txt", "w", encoding="utf-8") as f:
    f.write("\n=== RESULTATS DE RECHERCHE ===\n\n")
    for i, doc in enumerate(results, 1):
        f.write(f"{i}. {doc['filename']}\n")
        f.write(f"   Score total: {doc['similarity_score']:.1f}\n")

        if doc.get("score_breakdown"):
            breakdown = doc["score_breakdown"]
            f.write(f"   Detail du score:\n")
            for key, value in breakdown.items():
                f.write(f"      - {key}: {value:.1f}\n")  # Afficher TOUT, même 0
        else:
            f.write(f"   PAS DE BREAKDOWN!\n")
        f.write("\n")

print("Resultats ecrits dans test_results.txt")
