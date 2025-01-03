import tkinter as tk
from fingeprint import FingerprintApp

def main():
    root = tk.Tk()
    app = FingerprintApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()