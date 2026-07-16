import cramjam
def decompress(data):
    return bytes(cramjam.snappy.decompress_raw(bytes(data)))
def compress(data):
    return bytes(cramjam.snappy.compress_raw(bytes(data)))
