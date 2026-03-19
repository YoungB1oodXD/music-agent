import pandas as pd
import numpy as np

df = pd.read_csv('dataset/raw/fma_metadata/fma_metadata/tracks.csv', index_col=0, header=[0,1], nrows=1000)

print('=== FMA Tags Analysis ===')

track_tags_col = ('track', 'tags')
album_tags_col = ('album', 'tags')
artist_tags_col = ('artist', 'tags')

def is_non_empty(x):
    if pd.isna(x):
        return False
    s = str(x).strip()
    if s == '' or s == '[]' or s == 'nan':
        return False
    return True

track_tags_cover = df[track_tags_col].apply(is_non_empty).sum()
album_tags_cover = df[album_tags_col].apply(is_non_empty).sum()
artist_tags_cover = df[artist_tags_col].apply(is_non_empty).sum()

print(f'Track tags: {track_tags_cover}/1000 = {track_tags_cover/10:.1f}%')
print(f'Album tags: {album_tags_cover}/1000 = {album_tags_cover/10:.1f}%')
print(f'Artist tags: {artist_tags_cover}/1000 = {artist_tags_cover/10:.1f}%')

print('\n=== Sample Tags ===')
for i, row in df.head(20).iterrows():
    tt = row[track_tags_col]
    if is_non_empty(tt):
        print(f'Track {i}: {tt}')
        break

print('\n=== Genres Column ===')
genres_col = ('track', 'genres')
genre_top_col = ('track', 'genre_top')

genres_cover = df[genres_col].apply(is_non_empty).sum()
genre_top_cover = df[genre_top_col].apply(is_non_empty).sum()

print(f'genres column: {genres_cover}/1000 = {genres_cover/10:.1f}%')
print(f'genre_top column: {genre_top_cover}/1000 = {genre_top_cover/10:.1f}%')

print('\nSample genres values:')
for i, row in df.head(10).iterrows():
    g = row[genres_col]
    gt = row[genre_top_col]
    if is_non_empty(g):
        print(f'{i}: genres={g}, genre_top={gt}')

print('\n=== Audio Path Check ===')
for col in df.columns:
    col_str = str(col).lower()
    if 'path' in col_str or 'file' in col_str or 'audio' in col_str:
        print(f'{col}: {df[col].head(3).tolist()}')

print('\n=== All Available Columns ===')
print([str(c) for c in df.columns])