import random
import string


def random_id(length: int = 10) -> str:
    """Generate a random string."""
    return "".join([random.choice(string.digits) for _ in range(length)])


class dummy:
    pass
