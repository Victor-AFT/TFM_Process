import os
import json
import pandas as pd

ROOT_DIR = "ADReSSo21"
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac"}


def find_audio(audio_id, root_dir, must_contain=None):
    """
    Busca un audio por ID.
    - must_contain: string que debe aparecer en la ruta (ej: 'normalizado')
    """
    for root, _, files in os.walk(root_dir):
        if must_contain and must_contain not in root.lower():
            continue

        for f in files:
            name, ext = os.path.splitext(f)
            if name == audio_id and ext.lower() in AUDIO_EXTENSIONS:
                return os.path.join(root, f)

    return None


def build_dataset_from_csv(root_dir):
    dataset = {}

    for root, _, files in os.walk(root_dir):
        for file in files:
            if not file.endswith(".csv"):
                continue

            csv_path = os.path.join(root, file)
            audio_id = os.path.splitext(file)[0]

            label = "decline" if "decline" in root.lower() else "no_decline"

            # 🔹 leer CSV (info del audio NO normalizado)
            try:
                df = pd.read_csv(csv_path)
            except Exception as e:
                print(f"Error leyendo {csv_path}: {e}")
                continue

            # 🔹 buscar audios
            audio_no_norm = find_audio(audio_id, root_dir, must_contain="audio")
            audio_norm = find_audio(audio_id, root_dir, must_contain="normalizado")

            dataset[audio_id] = {
                "label": label,
                "audio_no_normalizado": audio_no_norm,
                "audio_normalizado": audio_norm,
                "csv": {
                    "path": csv_path,
                    "rows": df.to_dict(orient="records")
                }
            }

    return dataset


def main():
    dataset = build_dataset_from_csv(ROOT_DIR)

    with open("adress21_from_non_normalized.json", "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"JSON generado con {len(dataset)} muestras")


if __name__ == "__main__":
    main()
