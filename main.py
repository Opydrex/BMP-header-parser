import tkinter as tk
import tkinter.filedialog
def browse():                                                   # Function to replace the user filepath with a selected file
    filepath = tk.filedialog.askopenfilename()
    user_fp.delete(0, tk.END)
    user_fp.insert(0, filepath)
    
## Initializing the Window
window = tk.Tk()                                                # This initializes the window object
window.geometry("720x512")                                      # sets the window resolution
window.title("BMP File Decoder")                                # sets the title of the window

label = tk.Label(window, text="File Path",padx=10, pady=10)
label.grid(row=0, column=0)

metadata = tk.Label(window, text=txt, padx=10, pady=10)
metadata.grid(row=2, column=0)

user_fp = tk.Entry(window, width=50)                            # text entry box to let the user enter a file path
user_fp.grid(row=0, column=1)

browse_button = tk.Button(window,width=5,text="Browse", command=browse).grid(row=0,column=2)
window.mainloop()                                               # This actually starts the window
