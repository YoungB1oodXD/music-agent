#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Data Quality Audit Script"""

import pandas as pd
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def main():
    print("=" * 60)
    print("DATA QUALITY AUDIT")
    print("=" * 60)
    
    # Load parquet
    df = pd.read_parquet('data/processed/unified_songs_bge.parquet')
    
    print(f"\nTotal records: {len(df):,}")
    print(f"Columns: {df.columns.tolist()}")
    
    print("\n--- Column Analysis ---")
    
    # track_id
    print(f"\ntrack_id:")
    print(f"  Unique: {df['track_id'].nunique():,}")
    print(f"  Duplicates: {len(df) - df['track_id'].nunique():,}")
    
    # title
    empty_title = (df['title'] == '').sum() + df['title'].isna().sum()
    print(f"\ntitle:")
    print(f"  Empty: {empty_title:,} ({empty_title/len(df)*100:.2f}%)")
    
    # artist
    empty_artist = (df['artist'] == '').sum() + df['artist'].isna().sum()
    print(f"\nartist:")
    print(f"  Empty: {empty_artist:,} ({empty_artist/len(df)*100:.2f}%)")
    
    # genre
    empty_genre = (df['genre'] == '').sum() + df['genre'].isna().sum()
    print(f"\ngenre:")
    print(f"  Empty: {empty_genre:,} ({empty_genre/len(df)*100:.2f}%)")
    print(f"  Unique genres: {df['genre'].nunique()}")
    print(f"  Genre distribution (top 10):")
    for g, c in df['genre'].value_counts().head(10).items():
        print(f"    {g or '(empty)'}: {c:,}")
    
    # tags
    empty_tags = df['tags'].apply(lambda x: len(x) == 0 if isinstance(x, list) else True).sum()
    print(f"\ntags:")
    print(f"  Empty: {empty_tags:,} ({empty_tags/len(df)*100:.2f}%)")
    non_empty_tags = df[df['tags'].apply(lambda x: len(x) > 0 if isinstance(x, list) else False)]
    if len(non_empty_tags) > 0:
        all_tags = []
        for t in non_empty_tags['tags']:
            all_tags.extend(t)
        print(f"  Total tag instances: {len(all_tags):,}")
        print(f"  Unique tags: {len(set(all_tags)):,}")
    
    # rich_text
    print(f"\nrich_text:")
    lengths = df['rich_text'].str.len()
    print(f"  Min length: {lengths.min()}")
    print(f"  Max length: {lengths.max()}")
    print(f"  Mean length: {lengths.mean():.1f}")
    
    # Duplicates
    print(f"\n--- Duplicate Analysis ---")
    title_artist_combo = df['title'] + '|||' + df['artist']
    dup_combo = title_artist_combo.duplicated().sum()
    print(f"  Duplicate title+artist: {dup_combo:,} ({dup_combo/len(df)*100:.2f}%)")
    
    # Sample data
    print(f"\n--- Sample Records ---")
    for i, row in df.head(3).iterrows():
        print(f"\n  Record {i}:")
        print(f"    track_id: {row['track_id']}")
        print(f"    title: {row['title']}")
        print(f"    artist: {row['artist']}")
        print(f"    genre: {row['genre']}")
        print(f"    tags: {row['tags'][:3] if row['tags'] else []}")
        print(f"    rich_text: {row['rich_text'][:100]}...")

if __name__ == '__main__':
    main()