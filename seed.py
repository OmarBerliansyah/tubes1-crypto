import random

def coordinates(idx,w,h):
    f_idx = idx // (w * h)
    rem = idx % (w * h)
    y = rem // w
    x = rem % w
    return f_idx, y, x

def random_seed(seed, total, limit):
    random.seed(seed)
    return random.sample(range(limit), total)