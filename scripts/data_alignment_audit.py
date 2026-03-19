#!/usr/bin/env python3
import os
import sys
import json
import pickle
from pathlib import Path
from collections import Counter

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np

def run_data_alignment_audit():
    output_path = project_root / ".sisyphus" / "tmp" / "data_alignment_audit.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    # 1. Load FMA metadata
    metadata_path = project_root / "dataset" / "processed" / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            fma_metadata = json.load(f)
        fma_track_ids = set(fma_metadata.keys())
        results["fma"] = {
            "total_tracks": len(fma_track_ids),
            "sample_ids": list(fma_track_ids)[:5]
        }
    else:
        results["fma"] = {"error": "metadata.json not found"}
        fma_track_ids = set()
    
    # 2. Load CF model and mappings
    model_path = project_root / "data" / "models" / "implicit_model.pkl"
    mappings_path = project_root / "data" / "models" / "cf_mappings.pkl"
    
    if model_path.exists() and mappings_path.exists():
        with open(model_path, "rb") as f:
            cf_model = pickle.load(f)
        
        with open(mappings_path, "rb") as f:
            cf_mappings = pickle.load(f)
        
        item_mapping = cf_mappings.get("item_mapping", {})
        reverse_items = cf_mappings.get("reverse_items", {})
        
        cf_track_ids = set(item_mapping.keys())
        
        results["cf_model"] = {
            "total_items_in_model": len(reverse_items),
            "unique_track_ids_in_mapping": len(item_mapping),
            "sample_ids": list(cf_track_ids)[:5]
        }
        
        # 3. Calculate overlap
        overlap = fma_track_ids.intersection(cf_track_ids)
        results["overlap"] = {
            "fma_tracks": len(fma_track_ids),
            "cf_tracks": len(cf_track_ids),
            "matched_tracks": len(overlap),
            "match_rate_pct": round(len(overlap) / len(fma_track_ids) * 100, 2) if fma_track_ids else 0
        }
        
        # 4. Analyze user-item matrix sparsity
        if hasattr(cf_model, 'item_factors') and cf_model.item_factors is not None:
            n_items = cf_model.item_factors.shape[0]
            if hasattr(cf_model, 'user_factors') and cf_model.user_factors is not None:
                n_users = cf_model.user_factors.shape[0]
            else:
                n_users = "unknown"
            
            results["matrix"] = {
                "n_users": n_users,
                "n_items": n_items,
                "theoretical_interactions": n_users * n_items if isinstance(n_users, int) else "unknown"
            }
        
        # 5. CF score distribution analysis
        # Sample some recommendations to get score distribution
        from src.recommender.music_recommender import MusicRecommender
        recommender = MusicRecommender()
        
        all_scores = []
        sample_songs = list(recommender.metadata.keys())[:10]
        
        for song in sample_songs:
            res = recommender.recommend_by_song(song, top_k=20)
            recs = res.get("recommendations", [])
            for rec in recs:
                if isinstance(rec, dict):
                    score = rec.get("score", 0)
                    if isinstance(score, (int, float)):
                        all_scores.append(score)
        
        if all_scores:
            results["cf_score_distribution"] = {
                "count": len(all_scores),
                "min": float(min(all_scores)),
                "max": float(max(all_scores)),
                "mean": float(np.mean(all_scores)),
                "median": float(np.median(all_scores)),
                "std": float(np.std(all_scores)),
                "percentile_90": float(np.percentile(all_scores, 90)),
                "percentile_95": float(np.percentile(all_scores, 95)),
                "near_zero_count": sum(1 for s in all_scores if abs(s) < 1e-6),
                "near_zero_pct": round(sum(1 for s in all_scores if abs(s) < 1e-6) / len(all_scores) * 100, 2)
            }
        
        # 6. Analyze Last.fm data source
        lastfm_train_path = project_root / "dataset" / "raw" / "lastfm_train"
        lastfm_subset_path = project_root / "dataset" / "raw" / "lastfm_subset"
        
        lastfm_stats = {}
        for name, path in [("lastfm_train", lastfm_train_path), ("lastfm_subset", lastfm_subset_path)]:
            if path.exists():
                json_files = list(path.rglob("*.json"))
                lastfm_stats[name] = {
                    "json_file_count": len(json_files),
                    "exists": True
                }
            else:
                lastfm_stats[name] = {"exists": False}
        
        results["lastfm_source"] = lastfm_stats
        
        # 7. Calculate sparsity metrics
        # From the CF model, estimate actual interactions
        # The implicit library stores item/user factors, not the raw matrix
        # We can infer from mappings
        total_items_mapped = len(item_mapping)
        results["sparsity_analysis"] = {
            "items_with_cf_embedding": total_items_mapped,
            "fma_tracks_total": len(fma_track_ids),
            "coverage_ratio": round(total_items_mapped / len(fma_track_ids), 4) if fma_track_ids else 0,
            "note": "CF model trained on Last.fm subset, FMA tracks indexed separately - likely data source mismatch"
        }
        
    else:
        results["cf_model"] = {"error": "CF model or mappings not found"}
    
    # 8. ChromaDB stats
    try:
        import chromadb
        chroma_path = project_root / "index" / "chroma_bge_m3"
        if chroma_path.exists():
            client = chromadb.PersistentClient(path=str(chroma_path))
            collection = client.get_collection("music_bge_collection")
            chroma_count = collection.count()
            results["chromadb"] = {
                "total_documents": chroma_count,
                "collection_name": "music_bge_collection"
            }
    except Exception as e:
        results["chromadb"] = {"error": str(e)}
    
    # Write results
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("=" * 60)
    print("DATA ALIGNMENT AUDIT RESULTS")
    print("=" * 60)
    
    if "overlap" in results:
        print(f"\nFMA Tracks: {results['overlap']['fma_tracks']}")
        print(f"CF Tracks: {results['overlap']['cf_tracks']}")
        print(f"Matched: {results['overlap']['matched_tracks']} ({results['overlap']['match_rate_pct']}%)")
    
    if "cf_score_distribution" in results:
        print(f"\nCF Score Distribution:")
        print(f"  Min: {results['cf_score_distribution']['min']:.2e}")
        print(f"  Max: {results['cf_score_distribution']['max']:.2e}")
        print(f"  Mean: {results['cf_score_distribution']['mean']:.2e}")
        print(f"  Median: {results['cf_score_distribution']['median']:.2e}")
        print(f"  Near-zero (< 1e-6): {results['cf_score_distribution']['near_zero_pct']}%")
    
    if "sparsity_analysis" in results:
        print(f"\nSparsity Analysis:")
        print(f"  Items with CF embedding: {results['sparsity_analysis']['items_with_cf_embedding']}")
        print(f"  FMA tracks total: {results['sparsity_analysis']['fma_tracks_total']}")
        print(f"  Coverage ratio: {results['sparsity_analysis']['coverage_ratio']}")
    
    print(f"\nResults saved to {output_path}")
    
    return results

if __name__ == "__main__":
    run_data_alignment_audit()