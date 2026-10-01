"""Genera los tonos de alerta de Donexto (chime + voz robótica).

No corre en el build. Los mp3/ogg ya están en public/sounds/.
Requiere ffmpeg y edge-tts en un venv (sin costo):

  python3 -m venv /tmp/tts-venv
  /tmp/tts-venv/bin/pip install edge-tts
  /tmp/tts-venv/bin/python frontend/scripts/generate-alert-sounds.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

PHRASES = {
    "es": ("es-MX-DaliaNeural", "Nueva alerta de Donexto"),
    "en": ("en-US-JennyNeural", "New Donexto alert"),
    "fr": ("fr-FR-DeniseNeural", "Nouvelle alerte Donexto"),
    "it": ("it-IT-ElsaNeural", "Nuovo avviso Donexto"),
    "pt": ("pt-BR-FranciscaNeural", "Novo alerta da Donexto"),
}

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "sounds"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    work = Path("/tmp/donexto-alert-sounds")
    work.mkdir(parents=True, exist_ok=True)
    for lang, (voice, phrase) in PHRASES.items():
        spoken = work / f"{lang}.mp3"
        subprocess.run(
            ["edge-tts", "--voice", voice, "--text", phrase, "--write-media", str(spoken)],
            check=True,
        )
        mixed = work / f"alert-{lang}.wav"
        filt = (
            "sine=frequency=880:duration=0.12,"
            "afade=t=out:st=0.06:d=0.06[ch];"
            "[1:a]asetrate=44100*0.92,aresample=44100,atempo=1.05,"
            "tremolo=f=18:d=0.25,volume=1.3[v];"
            "[ch][v]amix=inputs=2:duration=longest:dropout_transition=0"
        )
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "sine=frequency=880:duration=0.18",
                "-i", str(spoken),
                "-filter_complex", filt,
                "-t", "2.4",
                str(mixed),
            ],
            check=True,
        )
        for ext, codec in (("mp3", ["-codec:a", "libmp3lame", "-q:a", "7"]), ("ogg", ["-codec:a", "libvorbis", "-q:a", "4"])):
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(mixed), *codec, str(OUT / f"alert-{lang}.{ext}")],
                check=True,
            )
        size = (OUT / f"alert-{lang}.mp3").stat().st_size
        if size > 100_000:
            raise SystemExit(f"{lang} mp3 is {size} bytes")
        print(lang, size)


if __name__ == "__main__":
    main()
