#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRANSCRIBIR VIDEO
Transcribe a texto el audio de un video o archivo de audio (mp4, mkv, mov,
mp3, wav, m4a...) usando faster-whisper, localmente en el PC. El contenido
no se sube a internet; solo se descarga el modelo la primera vez.

Genera, en la carpeta del video (o en --salida):
  <nombre>.txt  transcripción con marcas de tiempo [hh:mm:ss]
  <nombre>.srt  subtítulos (se pueden cargar en VLC junto al video)

La transcripción se guarda a medida que avanza: si se interrumpe,
lo ya procesado queda en los archivos.

Requiere: py -m pip install faster-whisper

Uso:
  py transcribir_video.py "C:\\Users\\Usuario\\Videos\\2026-11-11 09-05-42.mp4"
  py transcribir_video.py video.mp4 --modelo medium
  py transcribir_video.py                 (abre un selector de archivo)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# ─── Configuración ───
MODELOS_DISPONIBLES = ["tiny", "base", "small", "medium", "large-v3", "turbo"]
MODELO_POR_DEFECTO = "small"
IDIOMA_POR_DEFECTO = "es"
EXTENSIONES_ADMITIDAS = "*.mp4 *.mkv *.mov *.avi *.webm *.mp3 *.wav *.m4a *.ogg *.flac"

if getattr(sys, "frozen", False):  # empaquetado como .exe con PyInstaller
    CARPETA_SCRIPT = Path(sys.executable).parent.resolve()
else:
    CARPETA_SCRIPT = Path(__file__).parent.resolve()
RUTA_LOG = CARPETA_SCRIPT / "transcribir_video.log"

log = logging.getLogger("transcribir_video")

# Oculta el aviso de Hugging Face sobre symlinks en Windows (inofensivo).
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


def parchear_pyav() -> None:
    """Compatibilidad entre faster-whisper 1.2 y PyAV 16+.

    faster-whisper llama a av.open(..., metadata_errors="ignore"), parámetro
    que las versiones nuevas de PyAV eliminaron. Este parche lo descarta
    si PyAV no lo acepta, sin afectar al resto de la llamada.
    """
    import av

    open_original = av.open
    if getattr(open_original, "_parcheado", False):
        return

    def open_compatible(*args, **kwargs):
        try:
            return open_original(*args, **kwargs)
        except TypeError as error:
            if "metadata_errors" not in str(error):
                raise
            kwargs.pop("metadata_errors", None)
            return open_original(*args, **kwargs)

    open_compatible._parcheado = True
    av.open = open_compatible


def configurar_logging() -> None:
    """Envía los mensajes a la consola y a un archivo .log junto al script."""
    formato = logging.Formatter("%(asctime)s  %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S")
    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(logging.Formatter("%(message)s"))
    archivo = logging.FileHandler(RUTA_LOG, encoding="utf-8")
    archivo.setFormatter(formato)
    log.setLevel(logging.INFO)
    log.addHandler(consola)
    log.addHandler(archivo)


def formatear_tiempo(segundos: float, formato_srt: bool = False) -> str:
    """Convierte segundos a 'hh:mm:ss' (o 'hh:mm:ss,mmm' para SRT)."""
    total_ms = int(round(segundos * 1000))
    horas, resto = divmod(total_ms, 3_600_000)
    minutos, resto = divmod(resto, 60_000)
    segs, ms = divmod(resto, 1000)
    if formato_srt:
        return f"{horas:02d}:{minutos:02d}:{segs:02d},{ms:03d}"
    return f"{horas:02d}:{minutos:02d}:{segs:02d}"


def elegir_archivo() -> Path | None:
    """Abre un selector de archivo de Windows y devuelve la ruta elegida."""
    import tkinter as tk
    from tkinter import filedialog

    raiz = tk.Tk()
    raiz.withdraw()
    ruta = filedialog.askopenfilename(
        title="Elige el video o audio a transcribir",
        initialdir=str(Path.home() / "Videos"),
        filetypes=[("Video o audio", EXTENSIONES_ADMITIDAS), ("Todos los archivos", "*.*")],
    )
    raiz.destroy()
    return Path(ruta) if ruta else None


def transcribir(video: Path, modelo: str, idioma: str, carpeta_salida: Path) -> tuple[Path, Path]:
    """Transcribe el video y escribe los archivos .txt y .srt.

    Args:
        video: Ruta del video o audio de entrada.
        modelo: Nombre del modelo Whisper (ver MODELOS_DISPONIBLES).
        idioma: Código de idioma del audio, por ejemplo "es".
        carpeta_salida: Carpeta donde se guardan los resultados.

    Returns:
        Rutas del archivo .txt y del archivo .srt generados.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("Falta la librería faster-whisper. Instálala con:\n  py -m pip install faster-whisper")
    parchear_pyav()

    log.info("Cargando modelo '%s' (la primera vez se descarga, puede tardar)...", modelo)
    modelo_whisper = WhisperModel(modelo, device="auto", compute_type="int8")

    log.info("Analizando audio de: %s", video.name)
    segmentos, info = modelo_whisper.transcribe(
        str(video),
        language=idioma,
        beam_size=5,
        vad_filter=True,  # salta silencios: más rápido y menos texto inventado
        condition_on_previous_text=False,  # evita que repita frases en bucle
    )
    duracion = info.duration or 0.0
    log.info("Duración del audio: %s. Transcribiendo...", formatear_tiempo(duracion))

    ruta_txt = carpeta_salida / f"{video.stem}.txt"
    ruta_srt = carpeta_salida / f"{video.stem}.srt"
    inicio = time.monotonic()
    numero_srt = 0

    with ruta_txt.open("w", encoding="utf-8") as archivo_txt, ruta_srt.open("w", encoding="utf-8") as archivo_srt:
        archivo_txt.write(f"Transcripción de: {video.name}\n")
        archivo_txt.write(f"Duración: {formatear_tiempo(duracion)} | Modelo: {modelo} | Idioma: {idioma}\n\n")

        for segmento in segmentos:
            texto = segmento.text.strip()
            if not texto:
                continue
            numero_srt += 1
            archivo_txt.write(f"[{formatear_tiempo(segmento.start)}] {texto}\n")
            archivo_srt.write(
                f"{numero_srt}\n"
                f"{formatear_tiempo(segmento.start, True)} --> {formatear_tiempo(segmento.end, True)}\n"
                f"{texto}\n\n"
            )
            archivo_txt.flush()
            archivo_srt.flush()

            if duracion:
                porcentaje = min(100.0, segmento.end / duracion * 100)
                transcurrido = time.monotonic() - inicio
                sys.stdout.write(
                    f"\r  Avance: {porcentaje:5.1f}%  ({formatear_tiempo(segmento.end)} de "
                    f"{formatear_tiempo(duracion)})  tiempo: {formatear_tiempo(transcurrido)}   "
                )
                sys.stdout.flush()

    sys.stdout.write("\n")
    log.info("Listo en %s.", formatear_tiempo(time.monotonic() - inicio))
    return ruta_txt, ruta_srt


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transcribe un video o audio a texto (localmente, con Whisper).",
        epilog=(
            "Ejemplos:\n"
            '  py transcribir_video.py "C:\\Users\\Usuario\\Videos\\reunion.mp4"\n'
            "  py transcribir_video.py reunion.mp4 --modelo medium\n"
            "  py transcribir_video.py   (abre un selector de archivo)\n\n"
            "Modelos: tiny/base (rápidos, menos precisos), small (equilibrado),\n"
            "medium/turbo/large-v3 (más precisos, más lentos)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("video", nargs="?", type=Path, help="ruta del video o audio")
    parser.add_argument("--modelo", choices=MODELOS_DISPONIBLES, default=MODELO_POR_DEFECTO,
                        help=f"modelo Whisper (por defecto: {MODELO_POR_DEFECTO})")
    parser.add_argument("--idioma", default=IDIOMA_POR_DEFECTO,
                        help=f"idioma del audio (por defecto: {IDIOMA_POR_DEFECTO})")
    parser.add_argument("--salida", type=Path, help="carpeta de salida (por defecto: la del video)")
    return parser


def main() -> int:
    configurar_logging()
    args = crear_parser().parse_args()

    video = args.video or elegir_archivo()
    if video is None:
        log.info("No se eligió ningún archivo.")
        return 1
    video = video.expanduser().resolve()
    if not video.is_file():
        log.error("No encuentro el archivo: %s", video)
        return 1

    carpeta_salida = (args.salida or video.parent).resolve()
    carpeta_salida.mkdir(parents=True, exist_ok=True)

    try:
        ruta_txt, ruta_srt = transcribir(video, args.modelo, args.idioma, carpeta_salida)
    except KeyboardInterrupt:
        log.warning("\nInterrumpido. Lo transcrito hasta ahora quedó guardado en %s", carpeta_salida)
        return 130
    except Exception:
        log.exception("Error al transcribir. Detalle completo en %s", RUTA_LOG)
        return 1

    log.info("Transcripción: %s", ruta_txt)
    log.info("Subtítulos:    %s", ruta_srt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
