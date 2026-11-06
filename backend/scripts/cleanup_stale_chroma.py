
import argparse
import json
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

CHUNKS_FILE = ROOT_DIR / "data" / "processed" / "chunks.json"

CHROMA_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", "data/chroma"))
if not CHROMA_DIR.is_absolute():
    CHROMA_DIR = ROOT_DIR / CHROMA_DIR

COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME",
    "ou_documents_gemini",
)


def main():
    parser = argparse.ArgumentParser(
        description="Xoa cac ID trong ChromaDB khong con trong chunks.json."
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Thuc su xoa cac ID cu. Mac dinh chi kiem tra, khong xoa.",
    )
    args = parser.parse_args()

    with CHUNKS_FILE.open("r", encoding="utf-8") as f:
        chunks = json.load(f)

    json_ids = {
        str(chunk["id"])
        for chunk in chunks
        if isinstance(chunk, dict)
        and chunk.get("id")
        and isinstance(
            chunk.get("text", chunk.get("content", chunk.get("chunk_text"))),
            str,
        )
        and chunk.get(
            "text", chunk.get("content", chunk.get("chunk_text"))
        ).strip()
    }

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(name=COLLECTION_NAME)

    chroma_ids = set(collection.get(include=[])["ids"])
    stale_ids = sorted(chroma_ids - json_ids)
    missing_ids = json_ids - chroma_ids

    print(f"Chunks hop le trong JSON: {len(json_ids)}")
    print(f"Ban ghi trong ChromaDB: {len(chroma_ids)}")
    print(f"Chunk trong JSON chua co trong ChromaDB: {len(missing_ids)}")
    print(f"Ban ghi cu khong con trong JSON: {len(stale_ids)}")

    if missing_ids:
        print("\nCANH BAO: Van con chunk thieu trong ChromaDB.")
        print("Hay dong bo embedding truoc khi don dep.")
        return

    if not stale_ids:
        print("\nChromaDB da dong bo. Khong co ID cu de xoa.")
        return

    if not args.delete:
        print("\nCHE DO KIEM TRA: Chua xoa du lieu nao.")
        print("Neu danh sach ID cu dung, chay lai voi tham so --delete.")
        print("\nMot vai ID cu:")
        for stale_id in stale_ids[:10]:
            print(f"  {stale_id}")
        if len(stale_ids) > 10:
            print(f"  ... va {len(stale_ids) - 10} ID khac")
        return

    # Lay lai ID moi nhat truoc khi xoa de tranh xoa nham ID hop le.
    latest_chroma_ids = set(collection.get(include=[])["ids"])
    latest_stale_ids = sorted(latest_chroma_ids - json_ids)

    if json_ids - latest_chroma_ids:
        print("\nHUY XOA: Phat hien chunk trong JSON bi thieu trong ChromaDB.")
        print("Hay kiem tra va dong bo lai truoc.")
        return

    if not latest_stale_ids:
        print("\nKhong con ID cu de xoa.")
        return

    collection.delete(ids=latest_stale_ids)

    remaining_ids = set(collection.get(include=[])["ids"])
    remaining_stale_ids = remaining_ids - json_ids

    print(f"\nDa xoa {len(latest_stale_ids)} ID cu.")
    print(f"So ban ghi con lai trong ChromaDB: {len(remaining_ids)}")
    print(f"So ID cu con sot lai: {len(remaining_stale_ids)}")


if __name__ == "__main__":
    main()
