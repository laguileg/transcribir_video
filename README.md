# Transcribir video

Transcribe a texto el audio de un video o audio (mp4, mkv, mov, mp3, wav, m4a...) usando
[faster-whisper](https://github.com/SYSTRAN/faster-whisper), **localmente en el PC**.
El contenido no se sube a internet; solo se descarga el modelo la primera vez.

Genera, en la carpeta del video:

- `<nombre>.txt`: transcripción con marcas de tiempo `[hh:mm:ss]`
- `<nombre>.srt`: subtítulos (se pueden cargar en VLC junto al video)

## Instalación (cmd)

```bat
cd C:\proyectos\transcribir_video
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
```

## Uso

```bat
py transcribir_video.py "C:\Users\Usuario\Videos\reunion.mp4"
py transcribir_video.py reunion.mp4 --modelo medium
py transcribir_video.py
```

Sin argumentos abre un selector de archivo.

| Modelo | Velocidad | Precisión |
|---|---|---|
| `tiny`, `base` | muy rápido | baja |
| `small` (por defecto) | equilibrado | buena |
| `medium`, `turbo`, `large-v3` | lento | muy buena |

Los videos, audios y transcripciones no se versionan (ver `.gitignore`).

## Licencia

[MIT](LICENSE): puedes usar, modificar y compartir este código libremente, manteniendo el aviso de autoría.
