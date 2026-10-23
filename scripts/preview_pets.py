"""Render the actual Qt sprites and selector without network/audio or user settings."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication
from desktop_pet.sprites import FRAME_FILES, load_pet_sprites
from desktop_pet.window import PetWindow
from desktop_pet.chat_style import pixel_font_family


def main():
    app = QApplication.instance() or QApplication([])
    output = Path(__file__).resolve().parent.parent / 'artifacts'
    output.mkdir(exist_ok=True)
    for pet_id in ('golden', 'hamster', 'rabbit'):
        canvas = QPixmap(800, 760)
        canvas.fill(QColor('#e8ede2'))
        painter = QPainter(canvas)
        painter.setFont(QFont(pixel_font_family(), 11))
        sprites = load_pet_sprites(pet_id)
        for row, (state, names) in enumerate(FRAME_FILES.items()):
            painter.setPen(QColor('#18211c'))
            painter.drawText(8, row*125+20, state)
            for frame in range(len(names)):
                painter.drawPixmap(100+frame*165, row*125, sprites.pixmap(state, frame=frame))
        painter.end()
        canvas.save(str(output / f'{pet_id}-poses.png'))
    with TemporaryDirectory(dir=output) as folder:
        settings = QSettings(str(Path(folder)/'settings.ini'), QSettings.Format.IniFormat)
        for key in ('physics/enabled', 'sound/effects', 'sound/purr', 'autonomy/enabled', 'nap/enabled'):
            settings.setValue(key, False)
        w = PetWindow(settings=settings)
        w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        w.show()
        for pet_id, response in (
                ('golden', '¡Vamos paso a paso! Yo te acompaño.'),
                ('hamster', '¡Hola! ¿Qué descubrimos hoy?'),
                ('rabbit', '¡Hola! ¿Damos un saltito hacia esa idea?')):
            w.set_pet(pet_id)
            w.show_response(response)
            app.processEvents()
            w.grab().save(str(output / f'{pet_id}-interface.png'))
        w.pet_menu.ensurePolished()
        w.pet_menu.adjustSize()
        w.pet_menu.grab().save(str(output/'pet-selector.png'))
        w.close()
    print('Previews:', output)


if __name__ == '__main__':
    main()
