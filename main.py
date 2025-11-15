import tkinter as tk
from tkinter import messagebox
import tkinter.filedialog
import numpy as np
from PIL import Image
from PIL import ImageTk
import time
from collections import Counter, deque
import os
import struct

global np_pixel_data
np_pixel_data = None
global current_bmp_path
current_bmp_path = None
global meta_frame
meta_frame = None

# ============= HUFFMAN CODING IMPLEMENTATION =============

class HuffmanNode:
    """Node for building Huffman tree"""
    def __init__(self, byte, freq):
        self.byte = byte
        self.freq = freq
        self.left = None
        self.right = None
    
    def __lt__(self, other):
        return self.freq < other.freq

def build_huffman_tree(data):
    """Build Huffman tree from byte data"""
    if len(data) == 0:
        return None
    
    # Count frequency of each byte value
    frequency = Counter(data)
    
    # Handle single unique byte case
    if len(frequency) == 1:
        byte_val = list(frequency.keys())[0]
        root = HuffmanNode(byte_val, frequency[byte_val])
        return root
    
    # Build priority queue
    import heapq
    heap = [HuffmanNode(byte, freq) for byte, freq in frequency.items()]
    heapq.heapify(heap)
    
    # Build tree
    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        
        parent = HuffmanNode(None, left.freq + right.freq)
        parent.left = left
        parent.right = right
        
        heapq.heappush(heap, parent)
    
    return heap[0]

def build_huffman_codes(root):
    """Generate Huffman codes from tree"""
    if root is None:
        return {}
    
    # Handle single byte case
    if root.byte is not None:
        return {root.byte: '0'}
    
    codes = {}
    
    def traverse(node, code):
        if node is None:
            return
        
        if node.byte is not None:
            codes[node.byte] = code
            return
        
        traverse(node.left, code + '0')
        traverse(node.right, code + '1')
    
    traverse(root, '')
    return codes

def huffman_compress(data):
    """Compress data using Huffman coding"""
    if len(data) == 0:
        return bytes(), None, 0
    
    # Build tree and codes
    tree = build_huffman_tree(data)
    codes = build_huffman_codes(tree)
    
    # Encode data
    encoded_bits = ''.join(codes[byte] for byte in data)
    
    # Convert bit string to bytes
    padding = (8 - len(encoded_bits) % 8) % 8
    encoded_bits += '0' * padding
    
    encoded_bytes = bytearray()
    for i in range(0, len(encoded_bits), 8):
        byte = int(encoded_bits[i:i+8], 2)
        encoded_bytes.append(byte)
    
    return bytes(encoded_bytes), tree, padding

def huffman_decompress(compressed_data, tree, padding):
    """Decompress Huffman encoded data"""
    if tree is None or len(compressed_data) == 0:
        return bytes()
    
    # Convert bytes to bit string
    bit_string = ''.join(format(byte, '08b') for byte in compressed_data)
    
    # Remove padding
    if padding > 0:
        bit_string = bit_string[:-padding]
    
    # Handle single byte tree
    if tree.byte is not None:
        # All bits decode to the same byte
        return bytes([tree.byte] * len(bit_string))
    
    # Decode using tree
    decoded = bytearray()
    current = tree
    
    for bit in bit_string:
        if bit == '0':
            current = current.left
        else:
            current = current.right
        
        if current.byte is not None:
            decoded.append(current.byte)
            current = tree
    
    return bytes(decoded)

# ============= CUSTOM HUFFMAN TREE SERIALIZATION =============

#Serialize Huffman tree to bytes without pickle
def serialize_huffman_tree(node):
    if node is None:
        return b''
    
    result = bytearray()
    
    def serialize_node(current_node):
        if current_node is None:
            return
        
        # Node marker, 0 for leaf, 1 for internal
        if current_node.byte is not None:
            # Leaf node: marker (0) + byte value
            result.append(0)
            result.append(current_node.byte)
        else:
            # Internal node: marker (1)
            result.append(1)
            serialize_node(current_node.left)
            serialize_node(current_node.right)
    
    serialize_node(node)
    return bytes(result)

#Deserialize Huffman tree from bytes without pickle
def deserialize_huffman_tree(data):
    if not data:
        return None
    
    data_queue = deque(data)
    
    def deserialize_node():
        if not data_queue:
            return None
        
        marker = data_queue.popleft()
        
        if marker == 0:  # Leaf node
            if data_queue:
                byte_val = data_queue.popleft()
                return HuffmanNode(byte_val, 0)
            else:
                return None
        elif marker == 1:  # Internal node
            node = HuffmanNode(None, 0)
            node.left = deserialize_node()
            node.right = deserialize_node()
            return node
        else:
            return None
    
    return deserialize_node()

# ============= RLE COMPRESSION IMPLEMENTATION =============


#Compress data using Run-Length Encoding
def rle_compress(data):
    if len(data) == 0:
        return bytes()
    
    compressed = bytearray()
    i = 0
    
    while i < len(data):
        count = 1
        # Count consecutive identical bytes
        while i + count < len(data) and data[i + count] == data[i] and count < 255:
            count += 1
        
        if count > 3:
            # Use RLE encoding: [0xFF, count, byte]
            compressed.append(0xFF)
            compressed.append(count)
            compressed.append(data[i])
            i += count
        else:
            # Copy bytes directly
            # Find run of non-repeating bytes
            run_start = i
            while i < len(data):
                # Check if next 4 bytes are the same (would be better to compress)
                if i + 3 < len(data) and data[i] == data[i+1] == data[i+2] == data[i+3]:
                    break
                i += 1
                # Stop if we've processed enough or found a compressible run
                if i - run_start >= 255 or (i < len(data) and data[i] == data[i-1] == data[i-2]):
                    break
            
            literal_count = i - run_start
            compressed.append(literal_count)
            compressed.extend(data[run_start:i])
    
    return bytes(compressed)

#Decompress RLE encoded data
def rle_decompress(data):
    if len(data) == 0:
        return bytes()
    
    decompressed = bytearray()
    i = 0
    
    while i < len(data):
        count_byte = data[i]
        i += 1
        
        if count_byte == 0xFF:  # RLE sequence
            if i + 1 < len(data):
                count = data[i]
                byte_val = data[i + 1]
                decompressed.extend([byte_val] * count)
                i += 2
        else:  # Literal sequence
            literal_count = count_byte
            if i + literal_count <= len(data):
                decompressed.extend(data[i:i + literal_count])
                i += literal_count
    
    return bytes(decompressed)

# ============= COMPRESSION FUNCTIONS =============

#Compress current BMP file to .cmpt365 format
def compress_bmp():
    global current_bmp_path
    
    if current_bmp_path is None or np_pixel_data is None:
        messagebox.showerror("Error", "Please open a BMP file first")
        return
    
    try:
        start_time = time.time()
        
        # Read original BMP file
        with open(current_bmp_path, 'rb') as f:
            bmp_data = f.read()
        
        original_size = len(bmp_data)
        
        # Parse BMP metadata
        width = int.from_bytes(bmp_data[18:22], "little")
        height = int.from_bytes(bmp_data[22:26], "little")
        bpp = int.from_bytes(bmp_data[28:30], "little")
        pixel_offset = int.from_bytes(bmp_data[10:14], "little")
        
        # Extract pixel data only (this is what we compress)
        pixel_data = bmp_data[pixel_offset:]
        
        # Extract color table if present
        color_table = bytes()
        if bpp <= 8:
            color_table = bmp_data[54:pixel_offset]
        
        # Try different compression methods
        compression_methods = []
        
        # Method 1: Huffman only
        huffman_compressed, huffman_tree, huffman_padding = huffman_compress(pixel_data)
        huffman_tree_bytes = serialize_huffman_tree(huffman_tree)
        
        # Build .cmpt365 file for Huffman
        huffman_cmpt_data = bytearray()
        huffman_cmpt_data.extend(b'CMPT365')  # 7 bytes signature
        huffman_cmpt_data.extend(width.to_bytes(4, 'little'))
        huffman_cmpt_data.extend(height.to_bytes(4, 'little'))
        huffman_cmpt_data.extend(bpp.to_bytes(2, 'little'))
        huffman_cmpt_data.extend((0).to_bytes(1, 'little'))  # Compression method: 0 = Huffman
        huffman_cmpt_data.extend(huffman_padding.to_bytes(1, 'little'))
        huffman_cmpt_data.extend(len(color_table).to_bytes(4, 'little'))
        huffman_cmpt_data.extend(len(huffman_tree_bytes).to_bytes(4, 'little'))
        huffman_cmpt_data.extend(color_table)
        huffman_cmpt_data.extend(huffman_tree_bytes)
        huffman_cmpt_data.extend(huffman_compressed)
        
        compression_methods.append(('Huffman', len(huffman_cmpt_data), huffman_cmpt_data))
        
        # Method 2: RLE + Huffman
        rle_compressed = rle_compress(pixel_data)
        rle_huffman_compressed, rle_huffman_tree, rle_huffman_padding = huffman_compress(rle_compressed)
        rle_huffman_tree_bytes = serialize_huffman_tree(rle_huffman_tree)
        
        # Build .cmpt365 file for RLE+Huffman
        rle_huffman_cmpt_data = bytearray()
        rle_huffman_cmpt_data.extend(b'CMPT365')  # 7 bytes signature
        rle_huffman_cmpt_data.extend(width.to_bytes(4, 'little'))
        rle_huffman_cmpt_data.extend(height.to_bytes(4, 'little'))
        rle_huffman_cmpt_data.extend(bpp.to_bytes(2, 'little'))
        rle_huffman_cmpt_data.extend((1).to_bytes(1, 'little'))  # Compression method: 1 = RLE+Huffman
        rle_huffman_cmpt_data.extend(rle_huffman_padding.to_bytes(1, 'little'))
        rle_huffman_cmpt_data.extend(len(color_table).to_bytes(4, 'little'))
        rle_huffman_cmpt_data.extend(len(rle_huffman_tree_bytes).to_bytes(4, 'little'))
        rle_huffman_cmpt_data.extend(color_table)
        rle_huffman_cmpt_data.extend(rle_huffman_tree_bytes)
        rle_huffman_cmpt_data.extend(rle_huffman_compressed)
        
        compression_methods.append(('RLE+Huffman', len(rle_huffman_cmpt_data), rle_huffman_cmpt_data))
        
        # Method 3: RLE only (for comparison)
        rle_only_compressed = rle_compress(pixel_data)
        
        rle_only_cmpt_data = bytearray()
        rle_only_cmpt_data.extend(b'CMPT365')  # 7 bytes signature
        rle_only_cmpt_data.extend(width.to_bytes(4, 'little'))
        rle_only_cmpt_data.extend(height.to_bytes(4, 'little'))
        rle_only_cmpt_data.extend(bpp.to_bytes(2, 'little'))
        rle_only_cmpt_data.extend((2).to_bytes(1, 'little'))  # Compression method: 2 = RLE only
        rle_only_cmpt_data.extend((0).to_bytes(1, 'little'))  # No padding for RLE
        rle_only_cmpt_data.extend(len(color_table).to_bytes(4, 'little'))
        rle_only_cmpt_data.extend((0).to_bytes(4, 'little'))  # No tree for RLE only
        rle_only_cmpt_data.extend(color_table)
        rle_only_cmpt_data.extend(rle_only_compressed)
        
        compression_methods.append(('RLE only', len(rle_only_cmpt_data), rle_only_cmpt_data))
        
        # Select best compression method
        best_method = min(compression_methods, key=lambda x: x[1])
        method_name, compressed_size, cmpt_data = best_method
        
        # Check if compression is effective
        if compressed_size >= original_size:
            result = messagebox.askyesno(
                "Compression Warning",
                f"Best method '{method_name}' produced file ({compressed_size:,} bytes) which is larger than original ({original_size:,} bytes).\n\n"
                f"This can happen with small files due to overhead.\n\n"
                f"Save anyway?"
            )
            if not result:
                return
        
        # Save file
        save_path = tkinter.filedialog.asksaveasfilename(
            defaultextension=".cmpt365",
            filetypes=[("CMPT365 files", "*.cmpt365"), ("All files", "*.*")]
        )
        
        if not save_path:
            return
        
        with open(save_path, 'wb') as f:
            f.write(cmpt_data)
        
        compression_ratio = original_size / compressed_size
        compression_time = (time.time() - start_time) * 1000
        
        show_compression_stats(original_size, compressed_size, compression_ratio, compression_time, method_name, compression_methods)
        
    except Exception as e:
        messagebox.showerror("Compression Error", f"Failed to compress: {str(e)}")

    #Display compression statistics
def show_compression_stats(original, compressed, ratio, time_ms, method_name, all_methods):
    stats_window = tk.Toplevel(window)
    stats_window.title("Compression Statistics")
    stats_window.geometry("500x350")
    
    tk.Label(stats_window, text="Compression Complete!", font=("Arial", 14, "bold")).pack(pady=10)
    
    stats_frame = tk.Frame(stats_window)
    stats_frame.pack(pady=10, padx=20, fill="both", expand=True)
    
    tk.Label(stats_frame, text=f"Selected Method: {method_name}", font=("Arial", 11, "bold")).pack(anchor="w", pady=2)
    tk.Label(stats_frame, text=f"Original File Size: {original:,} bytes", font=("Arial", 11)).pack(anchor="w", pady=2)
    tk.Label(stats_frame, text=f"Compressed File Size: {compressed:,} bytes", font=("Arial", 11)).pack(anchor="w", pady=2)
    tk.Label(stats_frame, text=f"Compression Ratio: {ratio:.4f}", font=("Arial", 11)).pack(anchor="w", pady=2)
    tk.Label(stats_frame, text=f"Compression Time: {time_ms:.2f} ms", font=("Arial", 11)).pack(anchor="w", pady=2)
   
    if ratio < 1.0:
        tk.Label(stats_frame, text="⚠ File increased in size", font=("Arial", 10), fg="red").pack(anchor="w", pady=5)
    
    tk.Button(stats_window, text="OK", command=stats_window.destroy, width=10).pack(pady=10)

#Open and decompress a .cmpt365 file
def open_cmpt365():
    filepath = tkinter.filedialog.askopenfilename(
        filetypes=[("CMPT365 files", "*.cmpt365"), ("All files", "*.*")]
    )
    
    if not filepath:
        return
    
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # Parse header
        if data[:7] != b'CMPT365':
            messagebox.showerror("Error", "Invalid .cmpt365 file")
            return
        
        pos = 7
        width = int.from_bytes(data[pos:pos+4], 'little')
        pos += 4
        height = int.from_bytes(data[pos:pos+4], 'little')
        pos += 4
        bpp = int.from_bytes(data[pos:pos+2], 'little')
        pos += 2
        compression_method = int.from_bytes(data[pos:pos+1], 'little')
        pos += 1
        padding = int.from_bytes(data[pos:pos+1], 'little')
        pos += 1
        color_table_len = int.from_bytes(data[pos:pos+4], 'little')
        pos += 4
        tree_len = int.from_bytes(data[pos:pos+4], 'little')
        pos += 4
        
        # Extract components
        color_table = data[pos:pos+color_table_len]
        pos += color_table_len
        
        tree_data = data[pos:pos+tree_len]
        pos += tree_len
        
        compressed_pixels = data[pos:]
        
        # Decompress based on method
        if compression_method == 0:  # Huffman only
            huffman_tree = deserialize_huffman_tree(tree_data)
            pixel_data = huffman_decompress(compressed_pixels, huffman_tree, padding)
        elif compression_method == 1:  # RLE + Huffman
            huffman_tree = deserialize_huffman_tree(tree_data)
            rle_data = huffman_decompress(compressed_pixels, huffman_tree, padding)
            pixel_data = rle_decompress(rle_data)
        elif compression_method == 2:  # RLE only
            pixel_data = rle_decompress(compressed_pixels)
        else:
            messagebox.showerror("Error", f"Unknown compression method: {compression_method}")
            return
        
        # Parse pixel data to image array
        global np_pixel_data, img_w, img_h, current_bmp_path, meta_frame
        img_w = width
        img_h = height
        current_bmp_path = filepath
        
        # Update metadata display
        try:
            meta_frame.destroy()
        except:
            pass
        
        meta_frame = tk.Frame(window, pady=30, padx=10)
        meta_frame.grid(row=1, column=0, sticky="n", columnspan=4)
        
        method_names = {0: "Huffman", 1: "RLE+Huffman", 2: "RLE only"}
        method_name = method_names.get(compression_method, "Unknown")
        
        tk.Label(meta_frame, text="File Metadata", font=20).pack(side="top")
        tk.Label(meta_frame, text=f"File size: {len(data)} bytes").pack(side="top")
        tk.Label(meta_frame, text=f"Image width: {width} px").pack(side="top")
        tk.Label(meta_frame, text=f"Image height: {height} px").pack(side="top")
        tk.Label(meta_frame, text=f"Bits per Pixel: {bpp} bits").pack(side="top")
        tk.Label(meta_frame, text=f"Compression Method: {method_name}").pack(side="top")
        
        # Reconstruct image array
        pixel_array = []
        idx = 0
        
        # Calculate padding
        if bpp == 1:
            row_bytes = ((width + 31) // 32) * 4
        elif bpp == 4:
            row_bytes = ((width * 4 + 31) // 32) * 4
        elif bpp == 8:
            row_bytes = ((width + 3) // 4) * 4
        else:  # 24
            row_bytes = ((width * 3 + 3) // 4) * 4
        
        for row in range(height):
            curr_row = []
            
            if bpp == 1:
                pixel_count = 0
                while pixel_count < width and idx < len(pixel_data):
                    byte = pixel_data[idx]
                    idx += 1
                    for bit_pos in range(7, -1, -1):
                        if pixel_count >= width:
                            break
                        table_idx = ((byte >> bit_pos) & 1) * 4
                        B, G, R = color_table[table_idx:table_idx+3]
                        curr_row.append((R, G, B))
                        pixel_count += 1
                # Skip row padding
                bytes_used = (width + 7) // 8
                padding_bytes = row_bytes - bytes_used
                idx += padding_bytes
            
            elif bpp == 4:
                pixel_count = 0
                while pixel_count < width and idx < len(pixel_data):
                    byte = pixel_data[idx]
                    idx += 1
                    
                    # First nibble
                    table_idx = ((byte >> 4) & 0xF) * 4
                    B, G, R = color_table[table_idx:table_idx+3]
                    curr_row.append((R, G, B))
                    pixel_count += 1
                    
                    # Second nibble
                    if pixel_count < width:
                        table_idx = (byte & 0xF) * 4
                        B, G, R = color_table[table_idx:table_idx+3]
                        curr_row.append((R, G, B))
                        pixel_count += 1
                # Skip row padding
                bytes_used = (width * 4 + 7) // 8
                padding_bytes = row_bytes - bytes_used
                idx += padding_bytes
            
            elif bpp == 8:
                for col in range(width):
                    if idx < len(pixel_data):
                        table_idx = pixel_data[idx] * 4
                        idx += 1
                        B, G, R = color_table[table_idx:table_idx+3]
                        curr_row.append((R, G, B))
                # Skip row padding
                padding_bytes = row_bytes - width
                idx += padding_bytes
            
            elif bpp == 24:
                for col in range(width):
                    if idx + 2 < len(pixel_data):
                        B = pixel_data[idx]
                        G = pixel_data[idx + 1]
                        R = pixel_data[idx + 2]
                        curr_row.append((R, G, B))
                        idx += 3
                # Skip row padding
                padding_bytes = row_bytes - (width * 3)
                idx += padding_bytes
            
            pixel_array.append(curr_row)
        
        np_pixel_data = np.array(pixel_array, dtype=np.uint8)
        np_pixel_data = np_pixel_data[::-1, :, :]  # Flip vertically
        
        draw_image(np_pixel_data)
        messagebox.showinfo("Success", f"Successfully decompressed .cmpt365 file\nMethod: {method_name}")
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open .cmpt365: {str(e)}")

# ============= ORIGINAL PA1 FUNCTIONS =============

def browse():
    filepath = tk.filedialog.askopenfilename()
    user_fp.delete(0, tk.END)
    user_fp.insert(0, filepath)

def open_file():
    global current_bmp_path, meta_frame
    try:
        filepath = str(user_fp.get())
        f = open(filepath, mode="rb")
        current_bmp_path = filepath
    except:
        messagebox.showerror(title="Could not open file", message="No file selected.")
        return

    bmp_bytes = f.read()
    if bmp_bytes[0:2] != b"BM":
        messagebox.showerror(title="File format Warning", message="Please select a BMP file")
        return
    
    # Clear old metadata
    try:
        meta_frame.destroy()
    except:
        pass
    
    meta_frame = tk.Frame(window, pady=30, padx=10)
    meta_frame.grid(row=1, column=0, sticky="n", columnspan=4)

    fsize = int.from_bytes(bmp_bytes[2:6], "little")
    global img_w, img_h
    img_w = int.from_bytes(bmp_bytes[18:22], "little")
    img_h = int.from_bytes(bmp_bytes[22:26], "little")
    img_bpp = int.from_bytes(bmp_bytes[28:30], "little")

    tk.Label(meta_frame, text="File Metadata", font=20).pack(side="top")
    tk.Label(meta_frame, text=f"File size: {fsize} bytes").pack(side="top")
    tk.Label(meta_frame, text=f"Image width: {img_w} px").pack(side="top")
    tk.Label(meta_frame, text=f"Image height: {img_h} px").pack(side="top")
    tk.Label(meta_frame, text=f"Bits per Pixel: {img_bpp} bits").pack(side="top")

    # Color Table
    pixel_data_offset = int.from_bytes(bmp_bytes[10:14], "little")
    c_table = bytes()
    if img_bpp <= 8:
        c_table = bmp_bytes[54:pixel_data_offset]

    # Pixel Data Parsing
    f.seek(pixel_data_offset)

    # Calculate padding
    if img_bpp == 1:
        row_bytes = ((img_w + 31) // 32) * 4
        padding = row_bytes - ((img_w + 7) // 8)
    elif img_bpp == 4:
        row_bytes = ((img_w * 4 + 31) // 32) * 4
        padding = row_bytes - ((img_w * 4 + 7) // 8)
    elif img_bpp == 8:
        row_bytes = ((img_w + 3) // 4) * 4
        padding = row_bytes - img_w
    else:  # 24
        row_bytes = ((img_w * 3 + 3) // 4) * 4
        padding = row_bytes - (img_w * 3)

    pixel_data = []
    for i in range(img_h):
        curr_row = []
        
        if img_bpp == 1:
            pixel_count = 0
            while pixel_count < img_w:
                byte = ord(f.read(1))
                for b in range(7, -1, -1):
                    if pixel_count >= img_w:
                        break
                    table_idx = ((byte >> b) & 1) * 4
                    B, G, R = c_table[table_idx:table_idx + 3]
                    curr_row.append((R, G, B))
                    pixel_count += 1

        elif img_bpp == 4:
            pixel_count = 0
            while pixel_count < img_w:
                byte = ord(f.read(1))
                b1_table_idx = ((byte >> 4) & 0xF) * 4
                B, G, R = c_table[b1_table_idx:b1_table_idx + 3]
                curr_row.append((R, G, B))
                pixel_count += 1

                if pixel_count >= img_w:
                    break

                b2_table_idx = (byte & 0xF) * 4
                B, G, R = c_table[b2_table_idx:b2_table_idx + 3]
                curr_row.append((R, G, B))
                pixel_count += 1

        elif img_bpp == 8:
            for j in range(img_w):
                byte = ord(f.read(1))
                table_idx = byte * 4
                B, G, R = c_table[table_idx:table_idx + 3]
                curr_row.append((R, G, B))
                
        elif img_bpp == 24:
            for j in range(img_w):
                B = ord(f.read(1))
                G = ord(f.read(1))
                R = ord(f.read(1))
                curr_row.append((R, G, B))
        else:
            messagebox.showerror(title="Invalid Bit Depth", 
                               message="Please ensure your BMP file has a bit depth of 1, 4, 8 or 24.")
            return
            
        f.read(padding)
        pixel_data.append(curr_row)

    global np_pixel_data
    np_pixel_data = np.array(pixel_data, dtype=np.uint8)
    np_pixel_data = np_pixel_data[::-1, :, :]
    draw_image(np_pixel_data)

def draw_image(pixel_data):
    parsed_image = ImageTk.PhotoImage(Image.fromarray(pixel_data))
    image_label.config(image=parsed_image)
    image_label.image = parsed_image

def set_brightness(pixel_data):
    b_scale = brightness_scale.get() / 100
    pixel_data = (pixel_data * b_scale).astype(np.uint8)
    return pixel_data

def set_size(pixel_data):
    sz_scale = size_scale.get() / 100
    new_h = int(img_h * sz_scale)
    new_w = int(img_w * sz_scale)
    scaled_pixel_data = np.zeros((new_h, new_w, 3), dtype=np.uint8)
    for i in range(new_h):
        for j in range(new_w):
            scaled_i = int(i / sz_scale)
            scaled_j = int(j / sz_scale)
            scaled_pixel_data[i, j] = pixel_data[scaled_i, scaled_j]
    return scaled_pixel_data

R_on = 1
def toggle_R():
    global R_on
    R_on = 0 if R_on else 1
    modify_image()

G_on = 1
def toggle_G():
    global G_on
    G_on = 0 if G_on else 1
    modify_image()

B_on = 1
def toggle_B():
    global B_on
    B_on = 0 if B_on else 1
    modify_image()

def modify_image():
    modified_image = np_pixel_data.copy()
    modified_image = set_brightness(modified_image)
    modified_image = set_size(modified_image)
    if not R_on:
        modified_image[:, :, 0] = 0
    if not G_on:
        modified_image[:, :, 1] = 0
    if not B_on:
        modified_image[:, :, 2] = 0
    draw_image(modified_image)

# ============= GUI SETUP =============

window = tk.Tk()
window.geometry("1200x720")
window.title("BMP File Decoder with Compression")

## File path
file_label = tk.Label(window, text="File Path", padx=5, pady=10)
file_label.grid(row=0, column=0, sticky="e")

user_fp = tk.Entry(window, width=30)
user_fp.grid(row=0, column=1)

browse_button = tk.Button(window, width=7, text="Browse", command=browse)
browse_button.grid(row=0, column=2, padx=5)

open_button = tk.Button(window, width=5, text="Open", command=open_file)
open_button.grid(row=0, column=3, padx=5)

## Compression buttons
compress_button = tk.Button(window, width=18, text="Compress to .cmpt365", command=compress_bmp, bg="lightblue")
compress_button.grid(row=0, column=4, padx=5)

open_cmpt_button = tk.Button(window, width=18, text="Open .cmpt365", command=open_cmpt365, bg="lightgreen")
open_cmpt_button.grid(row=0, column=5, padx=5)

## Parsed Image
image_label = tk.Label(window, padx=50, pady=50)
image_label.grid(row=1, column=5, rowspan=3)

## Image Scale
size_frame = tk.Frame(window)
size_frame.grid(row=2, column=0, sticky="s", columnspan=4)

size_label = tk.Label(size_frame, text="Image Scale:")
size_label.pack(side="left", anchor="s")

size_scale = tk.Scale(size_frame, from_=0, to=100, orient="horizontal")
size_scale.pack(side="left")
size_scale.set(100)

size_button = tk.Button(size_frame, text="set", command=modify_image)
size_button.pack(side="left", anchor="s")

## Image Brightness
brightness_frame = tk.Frame(window)
brightness_frame.grid(row=3, column=0, sticky="s", columnspan=4)

brightness_label = tk.Label(brightness_frame, text="Brightness:")
brightness_label.pack(side="left", anchor="s", padx=4)

brightness_scale = tk.Scale(brightness_frame, from_=0, to=100, orient="horizontal")
brightness_scale.pack(side="left")
brightness_scale.set(100)

brightness_button = tk.Button(brightness_frame, text="set", command=modify_image)
brightness_button.pack(side="left", anchor="s")

## RGB Buttons
RGB_frame = tk.Frame(window, pady=150)
RGB_frame.grid(row=4, column=0, sticky="s", columnspan=3)

tk.Label(RGB_frame, text="RGB Toggle:", padx=5, pady=5).pack(side="left")
tk.Button(RGB_frame, text="R", fg="red", command=toggle_R).pack(side="left")
tk.Button(RGB_frame, text="G", fg="green", command=toggle_G).pack(side="left")
tk.Button(RGB_frame, text="B", fg="blue", command=toggle_B).pack(side="left")

window.mainloop()