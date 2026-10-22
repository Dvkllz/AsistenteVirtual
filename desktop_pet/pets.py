"""Small, immutable catalogue shared by UI, dialogue and asset loading."""

from dataclasses import dataclass
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / 'assets'


@dataclass(frozen=True)
class PetProfile:
    id: str
    label: str
    species: str
    friendly: bool = False

    @property
    def directory(self) -> Path:
        return ASSETS / self.id


PETS = {
    'siamese': PetProfile('siamese', 'Gato siamés · sarcástico', 'gato'),
    'golden': PetProfile('golden', 'Golden retriever · amigable', 'perro', True),
}
DEFAULT_PET = 'siamese'


def get_pet(pet_id=DEFAULT_PET) -> PetProfile:
    """Unknown persisted ids fall back to the original cat, never an arbitrary path."""
    return PETS.get(str(pet_id), PETS[DEFAULT_PET])
