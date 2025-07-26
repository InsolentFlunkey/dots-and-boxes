# Dots and Boxes (Desktop Edition)

A classic "Dots and Boxes" (also known as "Squares" or "Boxes") pencil-and-paper game, implemented as a Python desktop app using PySide6. Play against a computer opponent with a basic smart strategy.

---

## Features

- Variable grid sizes (choose your board size before each game)
- Customizable Player 1 name (remembers your name between runs)
- Modern, table-style scoreboard with current player highlighting
- Click lines to claim them; complete a square to score a point and take another turn
- Play against a computer opponent with simple “smart” logic (not perfect AI)
- Clean and modular code—easy to expand or tweak
- Improved UI and dark mode support

---

## Installation

1. **Install Python 3.10+**
   - [Download Python](https://www.python.org/downloads/) if you don't have it.
2. **(Optional but recommended) Create a virtual environment:**
   ```
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```
3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

---

## Running the Game

After completing the Installation steps above, run:
```
python dots_and_boxes.py
```

---

## How to Play

- **Player 1** clicks between two adjacent dots to draw a line (horizontal or vertical).
- If you complete the *fourth* side of any 1x1 box, you “claim” it (it will be shaded and labeled with your initial).
- Claiming a box gives you another turn.
- If no box is claimed, the turn passes to the computer.
- The computer uses a basic smart algorithm:
  - Completes boxes if possible.
  - Otherwise, avoids setting up the opponent to complete boxes, if possible.
- When all lines are claimed, the player with the most boxes wins!

---

## Project Goals & Roadmap

This project is intended to be **expanded and improved**. Some ideas for future features:

- [ ] **Undo/redo functionality**
- [ ] **Two-player (human vs. human) mode**
- [ ] **More advanced AI strategies**
- [ ] **Improved graphics/UI (e.g., animations, color themes)**
- [ ] **Game saving/loading**
- [ ] **Score/history tracking**
- [ ] **Packaging as an executable for Windows/macOS/Linux**
- [ ] Remember the selected grid size between sessions (store in player_config.json)
- [ ] Blink the line when a move is made (especially for computer moves)
- [ ] Add a 'Show last move' button to blink the last line
- [ ] Show a shadow/preview of the line on mouse hover before clicking

---

## About Dots and Boxes

“Dots and Boxes” is a classic pencil-and-paper game dating back to the 19th century (Édouard Lucas’s "La Pipopipette").
It is popular for its simple rules, but the endgame features surprisingly deep strategy.

---

## License

MIT (or add your preferred license)

---

## Credits

- [PySide6](https://doc.qt.io/qtforpython/)
- Game design: Édouard Lucas (original)
- Project maintained and extended by: Bryan Keary (and contributors!)

---

## Contributing

If you want to help grow this project, open an issue or submit a pull request with your ideas or code improvements!

