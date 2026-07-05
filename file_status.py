from enum import Enum


class FileStatus(Enum):
    PENDING = "Oczekuje"
    DONE = "Przekonwertowany"
    UNCONVERTIBLE = "Niekonwertowalny"
    EXISTING_PENDING = "Plik istnieje (konwertowalny)"
    EXISTING_UNCONVERTIBLE = "Plik istnieje (niekonwertowalny)"
