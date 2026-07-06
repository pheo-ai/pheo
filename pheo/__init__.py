from pheo.core.corpus import File, Folder, Text
from pheo.sdk import GovernedOutcome, PendingReview, Pheo


__version__ = "0.1.0"


def open(project="./.pheo"):
    return Pheo.open(project)


__all__ = ["Pheo", "GovernedOutcome", "PendingReview", "File", "Folder", "Text", "open"]
