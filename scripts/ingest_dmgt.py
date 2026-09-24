import os
from ingest.pipeline import ingest_file
import chromadb
from config import CHROMA_DIR
from pathlib import Path

dmgt_text = """
Discrete Mathematics & Graph Theory (DMGT).
Euler's formula for connected planar graphs states that if a finite, connected, planar graph is drawn in the plane without any edge intersections, and v is the number of vertices, e is the number of edges and f is the number of faces (regions bounded by edges, including the outer, infinitely large region), then:
$$v - e + f = 2$$
"""

os.makedirs("data/raw/DMGT", exist_ok=True)
with open("data/raw/DMGT/euler.txt", "w") as f:
    f.write(dmgt_text)

import chromadb
chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = chroma_client.get_or_create_collection("exam_brain")
ingest_file(Path("data/raw/DMGT/euler.txt"), "DMGT", collection)
print("DMGT file ingested.")
