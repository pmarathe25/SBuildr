def str_hash(obj):
    return f"{hash(obj) % ((sys.maxsize + 1) * 2)}"
