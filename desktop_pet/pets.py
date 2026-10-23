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
    atlas: bool = False
    atlas_targets: tuple[tuple[int, int], ...] = ((112, 100), (118, 57), (140, 82), (140, 100))
    head_idle: tuple[float, float, float, float] = (.38, .04, .46, .34)
    head_walking: tuple[float, float, float, float] = (.76, .16, .23, .34)
    mouth: tuple[int, int] = (65, 44)
    paw: tuple[int, int] = (128, 60)

    @property
    def directory(self) -> Path:
        return ASSETS / self.id


PETS = {
    'siamese': PetProfile('siamese', 'Gato siamés · sarcástico', 'gato'),
    'golden': PetProfile(
        'golden', 'Golden retriever · amigable', 'perro', friendly=True, atlas=True,
        head_idle=(.50, .03, .33, .36), head_walking=(.68, .26, .27, .32),
        mouth=(62, 46), paw=(128, 60)),
    'hamster': PetProfile(
        'hamster', 'Hámster · curioso', 'hámster', friendly=True, atlas=True,
        atlas_targets=((102, 92), (102, 70), (124, 72), (124, 90)),
        head_idle=(.55, .12, .38, .38), head_walking=(.64, .18, .32, .40),
        mouth=(56, 52), paw=(124, 64)),
    'rabbit': PetProfile(
        'rabbit', 'Conejo · alegre', 'conejo', friendly=True, atlas=True,
        atlas_targets=((102, 104), (106, 78), (132, 76), (132, 96)),
        head_idle=(.55, .04, .41, .44), head_walking=(.56, .04, .40, .48),
        mouth=(48, 40), paw=(132, 58)),
}
DEFAULT_PET = 'siamese'


def get_pet(pet_id=DEFAULT_PET) -> PetProfile:
    """Unknown persisted ids fall back to the original cat, never an arbitrary path."""
    return PETS.get(str(pet_id), PETS[DEFAULT_PET])
