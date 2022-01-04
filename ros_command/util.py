def sizeof_fmt(num, suffix='B'):
    # https://stackoverflow.com/questions/1094841/get-human-readable-version-of-file-size
    BASE = 1024.0
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < BASE:
            return f'{num:3.1f} {unit}{suffix}'
        num /= BASE
    return '{num:.1f} Yi{suffix}'
