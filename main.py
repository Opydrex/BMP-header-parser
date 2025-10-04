import tkinter as tk
from tkinter import messagebox
import tkinter.filedialog
import numpy as np
from PIL import Image
from PIL import ImageTk

global np_pixel_data
np_pixel_data = None

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
        meta_frame.grid(row=1,column=0,sticky="n",columnspan=4)

        fsize = int.from_bytes(bmp_bytes[2:6],"little")
        global img_w
        img_w = int.from_bytes(bmp_bytes[18:22],"little")
        global img_h
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

        if(img_bpp == 8):
            row_bytes = ((img_w + 3) // 4) * 4
            padding = row_bytes - img_w
        else:
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

        global np_pixel_data
        np_pixel_data = np.array(pixel_data, dtype=np.uint8)
        np_pixel_data = np_pixel_data[::-1, :, :]                     #BMP stores the pixels upside down, this flips them
        draw_image(np_pixel_data)
       
       
def draw_image(pixel_data):
    parsed_image = ImageTk.PhotoImage(Image.fromarray(pixel_data))

    image_label.config(image=parsed_image)
    image_label.image = parsed_image
 
        
        

def set_brightness(pixel_data):
    b_scale = brightness_scale.get()/100
    pixel_data = (pixel_data * b_scale).astype(np.uint8)
    return pixel_data 

def set_size(pixel_data):
    sz_scale = size_scale.get()/100
    new_h = int(img_h * sz_scale)
    new_w = int(img_w * sz_scale)
    scaled_pixel_data = np.zeros((new_h, new_w, 3), dtype=np.uint8) 
    for i in range(new_h):
        for j in range(new_w):
            scaled_i = int(i / sz_scale)
            scaled_j = int(j / sz_scale)
            scaled_pixel_data[i, j] = pixel_data[scaled_i, scaled_j]

    pixel_data = scaled_pixel_data
    return pixel_data

R_on = 1 
def toggle_R():
    global R_on
    if(R_on):
        R_on = 0
    else:
        R_on = 1
    
    modify_image()

G_on = 1 
def toggle_G():
    global G_on
    if(G_on):
        G_on = 0
    else:
        G_on = 1
    
    modify_image()



B_on = 1 
def toggle_B():
    global B_on
    if(B_on):
        B_on = 0
    else:
        B_on = 1

    modify_image()

def modify_image():
    modified_image= np_pixel_data.copy()
    modified_image = set_brightness(modified_image)
    modified_image = set_size(modified_image)
    if not R_on:
        modified_image[:, :, 0] = 0        
    if not G_on:
        modified_image[:, :, 1] = 0
    if not B_on:
        modified_image[:, :, 2] = 0
    
    draw_image(modified_image)

## Initializing the Window
window = tk.Tk()                                                # This initializes the window object
window.geometry("1200x720")                                      # sets the window resolution
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

## Parsed Image
image_label = tk.Label(window, padx = 50, pady  = 50)
image_label.grid(row = 1, column = 5, rowspan=3)

## Image Scale
size_frame = tk.Frame(window)
size_frame.grid(row=2, column=0,sticky="s",columnspan=4)

size_label = tk.Label(size_frame, text="Image Scale:")
size_label.pack(side="left", anchor="s")

size_scale = tk.Scale(size_frame, from_=0, to=100, orient="horizontal")
size_scale.pack(side="left")
size_scale.set(100)

size_button = tk.Button(size_frame,text="set",command=modify_image)
size_button.pack(side="left", anchor="s")


## Image Brightness
brightness_frame = tk.Frame(window)
brightness_frame.grid(row=3, column=0,sticky="s", columnspan=4)

brightness_label = tk.Label(brightness_frame,text="Brightness:")
brightness_label.pack(side="left", anchor="s", padx=4)

brightness_scale = tk.Scale(brightness_frame, from_=0, to=100, orient="horizontal")
brightness_scale.pack(side="left")
brightness_scale.set(100)

size_button = tk.Button(brightness_frame,text="set",command=modify_image)
size_button.pack(side="left", anchor="s")


## RGB Buttons
RGB_frame = tk.Frame(window, pady=150)                                    # Groups the buttons together
RGB_frame.grid(row=4,column=0,sticky="s",columnspan=3)

toggle_label= tk.Label(RGB_frame, text="RGB Toggle:",padx=5, pady=5).pack(side="left")
red_toggle = tk.Button(RGB_frame, text="R", fg="red",command=toggle_R).pack(side="left")
green_toggle = tk.Button(RGB_frame, text="G", fg="green", command=toggle_G).pack(side="left")
blue_toggle = tk.Button(RGB_frame, text="B", fg="blue",command=toggle_B).pack(side="left")

window.mainloop()                                               # This actually starts the GUI
