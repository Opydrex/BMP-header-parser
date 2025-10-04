import tkinter as tk
from tkinter import messagebox
import tkinter.filedialog
import numpy as np
from PIL import image

def browse():                                                   # Function to replace the user filepath with a selected file
    filepath = tk.filedialog.askopenfilename()
    user_fp.delete(0, tk.END)
    user_fp.insert(0, filepath)

def open_file():
    try:
        f = open(str(user_fp.get()), mode="rb")
    except:
        messagebox.showerror(title="Could not open file",message="No file selected.")

    bmp_bytes = f.read()
    if(bmp_bytes[0:2] != b"BM"):                                # Throw a warning if the file signature is not BM
       messagebox.showerror(title="File format Warning",message="Please select a BMP file")
    else:
        ## Metadata
        meta_frame = tk.Frame(window, pady=30, padx=10)         # Frame that holds all the labels for the metadata
        meta_frame.grid(row=1,column=0,sticky="s",columnspan=4)

        fsize = int.from_bytes(bmp_bytes[2:6],"little")
        img_w = int.from_bytes(bmp_bytes[18:22],"little")
        img_h = int.from_bytes(bmp_bytes[22:26],"little")
        img_bpp = int.from_bytes(bmp_bytes[28:30],"little")

        tk.Label(meta_frame, text="File Metadata", font=20).pack(side="top")
        tk.Label(meta_frame, text=("File size: " + str(fsize) + " bytes")).pack(side="top" )
        tk.Label(meta_frame, text=("Image width: " + str(img_w)) + " px").pack(side="top")
        tk.Label(meta_frame, text=("Image height: " + str(img_h) + " px")).pack(side="top")
        tk.Label(meta_frame, text=("Bits per Pixel: " + str(img_bpp) + " bits")).pack(side="top")


        ## Color Table
        pixel_data_offset = int.from_bytes(bmp_bytes[10:14], "little")
        if(img_bpp <= 8):
            c_table = bmp_bytes[54:pixel_data_offset]

        ## Pixel Data Parsing
        f.seek(pixel_data_offset)

        row_size = ((img_bpp * img_w - 31) // 32) * 4
        padding = max(0,row_size - ((img_bpp * img_w) // 8))

        pixel_data = []
        for i in range(img_h):
            curr_row = []
            if img_bpp == 1:
                pixel_count = 0
                while(pixel_count < img_w):
                        byte = ord(f.read(1))
                        for b in range(7, -1, -1):                  # Start from the most significant bit 
                            if(pixel_count >= img_w):
                                break
                            table_idx = (byte >> b) & 1
                            table_idx*= 4                     
                            B, G, R = c_table[table_idx: table_idx + 3]
                            curr_row.append((R, G, B))
                            pixel_count += 1

            elif img_bpp == 4:

                pixel_count = 0
                while(pixel_count < img_w):
                    byte = ord(f.read(1))
                    b1_table_idx = (byte >> 4) & 0xF
                    b1_table_idx *= 4
                    B, G, R = c_table[b1_table_idx: b1_table_idx + 3]
                    curr_row.append((R, G, B))
                    pixel_count += 1

                    if(pixel_count >= img_w):
                        break

                    b2_table_idx = byte & 0xF
                    b2_table_idx *= 4
                    B, G, R = c_table[b2_table_idx: b2_table_idx + 3]
                    curr_row.append((R, G, B))
                    pixel_count += 1

            elif (img_bpp == 8):
                for j in range(img_w):
                    byte = ord(f.read(1))
                    table_idx = byte * 4
                    B, G, R = c_table[table_idx: table_idx + 3]
                    curr_row.append((R, G, B))
            elif(img_bpp == 24):
                for j in range(img_w):
                    B = ord(f.read(1))
                    G = ord(f.read(1))
                    R = ord(f.read(1))
                    curr_row.append((R, G, B))
            else:
                messagebox.showerror(title="Invalid Bit Depth",message="Please ensure your BMP file has a bit depth of 1, 4, 8 or 24.")
            f.read(padding)
            pixel_data.append(curr_row)

        

def set_brightness():
    print("Not yet implemented, the slider value is: " + str(brightness_scale.get()))

def set_size():
    print("Not yet implemented, the slider value is: " + str(size_scale.get()))


## Initializing the Window
window = tk.Tk()                                                # This initializes the window object
window.geometry("720x512")                                      # sets the window resolution
window.title("BMP File Decoder")                                # sets the title of the window


## File path
file_label = tk.Label(window, text="File Path",padx=5, pady=10)
file_label.grid(row=0, column=0, sticky="e")

user_fp = tk.Entry(window, width=30)                            # text entry box to let the user enter a file path
user_fp.grid(row=0, column=1)

browse_button = tk.Button(window,width=7,text="Browse", command=browse)
browse_button.grid(row=0,column=2, padx=5)

open_button = tk.Button(window,width=5,text="open", command=open_file)
open_button.grid(row=0,column=3, padx=5)



## Image Scale
size_frame = tk.Frame(window)
size_frame.grid(row=2, column=0,sticky="s",columnspan=4)

size_label = tk.Label(size_frame, text="Image Scale:")
size_label.pack(side="left", anchor="s")

size_scale = tk.Scale(size_frame, from_=0, to=100, orient="horizontal")
size_scale.pack(side="left")
size_scale.set(100)

size_button = tk.Button(size_frame,text="set",command=set_size)
size_button.pack(side="left", anchor="s")


## Image Brightness
brightness_frame = tk.Frame(window)
brightness_frame.grid(row=3, column=0,sticky="s", columnspan=4)

brightness_label = tk.Label(brightness_frame,text="Brightness:")
brightness_label.pack(side="left", anchor="s", padx=4)

brightness_scale = tk.Scale(brightness_frame, from_=0, to=100, orient="horizontal")
brightness_scale.pack(side="left")
brightness_scale.set(100)

size_button = tk.Button(brightness_frame,text="set",command=set_brightness)
size_button.pack(side="left", anchor="s")


## RGB Buttons
RGB_frame = tk.Frame(window, pady=50)                                    # Groups the buttons together
RGB_frame.grid(row=4,column=0,sticky="s",columnspan=3)

toggle_label= tk.Label(RGB_frame, text="RGB Toggle:",padx=5, pady=5).pack(side="left")
red_toggle = tk.Button(RGB_frame, text="R", fg="red").pack(side="left")
red_toggle = tk.Button(RGB_frame, text="G", fg="green").pack(side="left")
red_toggle = tk.Button(RGB_frame, text="B", fg="blue").pack(side="left")

window.mainloop()                                               # This actually starts the GUI
