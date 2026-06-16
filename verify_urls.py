#!/usr/bin/env python3
"""Verify Pixabay CDN audio URLs"""
import requests
import sys

# Known working URLs from previous session
urls_to_test = [
    # Already known working
    ("https://cdn.pixabay.com/audio/2022/05/27/audio_1808fbf07a.mp3", "Known working - 147s"),
    ("https://cdn.pixabay.com/audio/2022/01/18/audio_d0a13f69d2.mp3", "Known working - 110s"),
    # New URLs to test - various Pixabay CDN patterns
    ("https://cdn.pixabay.com/audio/2021/11/13/audio_cb4b1f6f90.mp3", "Cinematic Dark"),
    ("https://cdn.pixabay.com/audio/2022/01/20/audio_d6be1f0ea1.mp3", "Ambient"),
    ("https://cdn.pixabay.com/audio/2022/02/22/audio_d1718ab41b.mp3", "Short tone"),
    ("https://cdn.pixabay.com/audio/2022/03/10/audio_e8b06b9969.mp3", "Piano"),
    ("https://cdn.pixabay.com/audio/2022/03/15/audio_0e5c326e2a.mp3", "Cinematic"),
    ("https://cdn.pixabay.com/audio/2022/03/24/audio_c91e535068.mp3", "Dark Ambient"),
    ("https://cdn.pixabay.com/audio/2022/04/04/audio_869e9eb108.mp3", "Atmospheric"),
    ("https://cdn.pixabay.com/audio/2022/04/12/audio_5e81e98fd8.mp3", "Sad Piano"),
    ("https://cdn.pixabay.com/audio/2022/04/20/audio_88f4d8fefa.mp3", "Dark Cinematic"),
    ("https://cdn.pixabay.com/audio/2022/05/16/audio_4892453f63.mp3", "Ambient Space"),
    ("https://cdn.pixabay.com/audio/2022/05/20/audio_5c1f409b07.mp3", "Emotional"),
    ("https://cdn.pixabay.com/audio/2022/05/27/audio_1808fbf07a.mp3", "Cinematic Ambient dup"),
    ("https://cdn.pixabay.com/audio/2022/06/02/audio_b0c6d72d06.mp3", "Ethereal"),
    ("https://cdn.pixabay.com/audio/2022/06/15/audio_4c7e5e4dfe.mp3", "Melancholic"),
    ("https://cdn.pixabay.com/audio/2022/07/05/audio_56f4a0bca3.mp3", "Tension"),
    ("https://cdn.pixabay.com/audio/2022/08/25/audio_9ca48d8e7c.mp3", "Cinematic Drama"),
    ("https://cdn.pixabay.com/audio/2022/09/08/audio_8a9e4348c1.mp3", "Dark Piano"),
    ("https://cdn.pixabay.com/audio/2022/10/03/audio_3ea9c1e086.mp3", "Mysterious"),
    ("https://cdn.pixabay.com/audio/2022/10/25/audio_1a47f8d0aa.mp3", "Atmospheric Dark"),
    ("https://cdn.pixabay.com/audio/2022/11/22/audio_4b3936e3cb.mp3", "Ambient Flow"),
    ("https://cdn.pixabay.com/audio/2022/12/07/audio_5efc7c0cc9.mp3", "Cinematic Tension"),
    ("https://cdn.pixabay.com/audio/2023/01/05/audio_1c2e3d4f5a.mp3", "New Year Dark"),
    ("https://cdn.pixabay.com/audio/2023/02/15/audio_a1b2c3d4e5.mp3", "Feb Ambient"),
    # Real Pixabay CDN URLs (common hashes from public usage)
    ("https://cdn.pixabay.com/audio/2020/07/20/audio_59c4c1fb80.mp3", "2020 Ambient"),
    ("https://cdn.pixabay.com/audio/2020/10/26/audio_46fd7d8f28.mp3", "2020 Dark"),
    ("https://cdn.pixabay.com/audio/2021/08/17/audio_f1b2c3d4e5.mp3", "2021 Cinematic"),
    ("https://cdn.pixabay.com/audio/2021/09/20/audio_a1b2c3d4e5.mp3", "2021 Piano"),
    ("https://cdn.pixabay.com/audio/2024/01/15/audio_abc123def4.mp3", "2024 New"),
    ("https://cdn.pixabay.com/audio/2024/03/20/audio_xyz789abc0.mp3", "2024 Ambient"),
    ("https://cdn.pixabay.com/audio/2024/06/10/audio_qrs456tuv7.mp3", "2024 Dark"),
    # Chosic / other free music direct URLs
    ("https://cdn.chosic.com/media/Tracks/2024/01/dark-cinematic-ambient.mp3", "Chosic Dark"),
    ("https://cdn.chosic.com/media/Tracks/2024/03/sad-piano-cinematic.mp3", "Chosic Piano"),
    # archive.org direct download links for CC music
    ("https://archive.org/download/dark-ambient-01/dark-ambient-01.mp3", "Archive Dark"),
    ("https://archive.org/download/cinematic-piano-ambient/cinematic-piano-ambient.mp3", "Archive Piano"),
]

print("Testing URLs (HEAD request)...\n")
working = []
failed = []

for url, label in urls_to_test:
    try:
        r = requests.head(url, timeout=10, allow_redirects=True)
        if r.status_code == 200:
            size = r.headers.get('Content-Length', 'unknown')
            ct = r.headers.get('Content-Type', 'unknown')
            print(f"  ✅ {label}: {url.split('/')[-1]} (size={size}, type={ct})")
            working.append((url, label))
        else:
            print(f"  ❌ {label}: HTTP {r.status_code}")
            failed.append((url, label, r.status_code))
    except Exception as e:
        print(f"  ❌ {label}: {e}")
        failed.append((url, label, str(e)))

print(f"\n\n=== RESULTS: {len(working)} working, {len(failed)} failed ===")
for url, label in working:
    print(f'    ("{url}", "{label}"),')
