from sentence_transformers import SentenceTransformer

# load model once
model = SentenceTransformer('all-MiniLM-L6-v2')


# -----------------------------
# TEXT → EMBEDDING
# -----------------------------
def embed_text(text: str):
    """
    Converts text into vector embedding
    """
    return model.encode(text).tolist()


# -----------------------------
# LIST OF PROFILES → EMBEDDINGS
# -----------------------------
def process_profiles(data):

    processed = []

    for item in data:

        text = f"{item['name']} {item['department']} {' '.join(item['research_areas'])}"

        embedding = embed_text(text)

        processed.append({
            "document": text,
            "embedding": embedding,
            "metadata": item
        })

    return processed