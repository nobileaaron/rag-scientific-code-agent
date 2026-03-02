def load_cpp_file(path):
    with open(path, "r") as file:
        return file.read()


def simple_chunk(text, chunk_size=500):
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i+chunk_size])
    return chunks