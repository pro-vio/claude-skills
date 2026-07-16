import cramjam
def decompress(data):
    return bytes(cramjam.zstd.decompress(bytes(data)))
def compress(data, level=3):
    return bytes(cramjam.zstd.compress(bytes(data), level))
