import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from PIL import Image, ImageTk
import numpy as np
import os
import json

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    print("Warning: tkinterdnd2 not available. Install with: pip install tkinterdnd2")

CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.color_match_config.json')

# Default settings
settings = {
    'last_ref_dir': '',
    'last_tgt_dir': '',
    'last_out_dir': '',
    'mask_color': [0, 0, 0],  # default mask color (pure black)
    'mask_tolerance': 0  # default tolerance: only exact black ignored
}


# Load / Save settings
def load_settings():
    global settings
    try:
        with open(CONFIG_PATH, 'r') as f:
            settings.update(json.load(f))
    except Exception:
        pass


def save_settings():
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(settings, f)
    except Exception:
        pass


def get_average_rgb(img, mask_color=None, tolerance=0):
    np_img = np.array(img)
    mask = np.ones(np_img.shape[:2], dtype=bool)
    if mask_color is not None:
        # Exclude pixels within tolerance of mask_color
        diff = np.abs(np_img.astype(int) - np.array(mask_color)[None, None, :])
        mask = ~(np.all(diff <= tolerance, axis=-1))
    if not np.any(mask):
        # all pixels masked, fallback to full average
        return np_img.mean(axis=(0, 1))
    return np_img[mask].mean(axis=0)


def shift_color(img, target_avg, source_avg):
    arr = np.array(img).astype(np.int16)
    diff = np.round(target_avg - source_avg).astype(np.int16)
    arr += diff
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def is_image_file(path):
    return os.path.splitext(path)[1].lower() in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp']


class ImagePool(tk.Frame):
    def __init__(self, master, title, last_dir_key):
        super().__init__(master, relief='groove', bd=2)
        self._original_relief = 'groove'  # Store original relief
        self.last_dir_key = last_dir_key
        self.pool_title = title  # Store the title for later reference
        self.images = []
        self.thumbs = []

        # Title and drag/drop indicator
        title_frame = ttk.Frame(self)
        title_frame.pack(fill='x')
        ttk.Label(title_frame, text=title).pack(side='left')

        if DND_AVAILABLE:
            self.drop_label = ttk.Label(title_frame, text="📁 Drop images here",
                                        foreground='gray', font=('Arial', 8))
            self.drop_label.pack(side='right')

        btns = ttk.Frame(self)
        btns.pack(fill='x')
        ttk.Button(btns, text='Add...', command=self.add_images).pack(side='left')
        ttk.Button(btns, text='Clear', command=self.clear).pack(side='left')

        # scrollable canvas
        self.canvas = tk.Canvas(self)
        self.scroll = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.inner = ttk.Frame(self.canvas)
        self.win = self.canvas.create_window((0, 0), window=self.inner, anchor='nw')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scroll.pack(side='right', fill='y')
        self.inner.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))

        # Setup drag and drop
        if DND_AVAILABLE:
            self.setup_drag_drop()

        # reorder on click-drag-release
        self.inner.bind('<Button-1>', self._on_click)
        self.inner.bind('<B1-Motion>', self._on_drag)
        self.inner.bind('<ButtonRelease-1>', self._on_release)
        self._drag_idx = None
        self._drag_start_y = 0

    def setup_drag_drop(self):
        """Setup drag and drop functionality for the image pool"""
        # Make the entire frame accept drops
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.on_drop)

        # Also register canvas and inner frame
        self.canvas.drop_target_register(DND_FILES)
        self.canvas.dnd_bind('<<Drop>>', self.on_drop)
        self.inner.drop_target_register(DND_FILES)
        self.inner.dnd_bind('<<Drop>>', self.on_drop)

        # Visual feedback on drag over
        self.dnd_bind('<<DragEnter>>', self.on_drag_enter)
        self.dnd_bind('<<DragLeave>>', self.on_drag_leave)
        self.canvas.dnd_bind('<<DragEnter>>', self.on_drag_enter)
        self.canvas.dnd_bind('<<DragLeave>>', self.on_drag_leave)
        self.inner.dnd_bind('<<DragEnter>>', self.on_drag_enter)
        self.inner.dnd_bind('<<DragLeave>>', self.on_drag_leave)

    def on_drag_enter(self, event):
        """Visual feedback when dragging over the drop zone"""
        self.canvas.config(bg='lightblue')
        # Store original relief to restore later
        self._original_relief = self.cget('relief')
        self.config(relief='solid', bd=3)

    def on_drag_leave(self, event):
        """Remove visual feedback when dragging away"""
        self.canvas.config(bg='white')
        self.config(relief=self._original_relief, bd=2)

    def on_drop(self, event):
        """Handle dropped files"""
        # Remove visual feedback
        self.canvas.config(bg='white')
        self.config(relief=self._original_relief, bd=2)

        # Parse dropped files
        files = self.tk.splitlist(event.data)
        image_files = [f for f in files if os.path.isfile(f) and is_image_file(f)]

        if image_files:
            # Update last directory setting
            if self.last_dir_key in settings:
                settings[self.last_dir_key] = os.path.dirname(image_files[0])

            # Add valid image files
            self.images.extend(image_files)
            self.refresh()
        else:
            messagebox.showwarning("No Images", "No valid image files were dropped")

    def add_images(self):
        paths = filedialog.askopenfilenames(
            title='Select Images', initialdir=settings[self.last_dir_key],
            filetypes=[('Image files', '*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp'), ('All files', '*.*')]
        )
        valid = [p for p in paths if is_image_file(p)]
        if valid:
            settings[self.last_dir_key] = os.path.dirname(valid[0])
            self.images += valid
            self.refresh()

    def clear(self):
        self.images.clear()
        self.thumbs.clear()
        self.refresh()

    def refresh(self):
        for w in self.inner.winfo_children(): w.destroy()
        self.thumbs.clear()
        for idx, path in enumerate(self.images, 1):
            frm = ttk.Frame(self.inner)
            frm.pack(fill='x', pady=2, padx=2)

            try:
                img = Image.open(path)
                img.thumbnail((80, 80), Image.Resampling.LANCZOS)
                tkimg = ImageTk.PhotoImage(img)
                self.thumbs.append(tkimg)
                lbl = tk.Label(frm, image=tkimg)
                lbl.pack(side='left')

                # Image info
                info_frame = ttk.Frame(frm)
                info_frame.pack(side='left', fill='x', expand=True, padx=5)
                ttk.Label(info_frame, text=os.path.basename(path), font=('Arial', 8)).pack(anchor='w')


            except Exception as e:
                # Show error thumbnail
                lbl = tk.Label(frm, text="❌", font=('Arial', 20), fg='red')
                lbl.pack(side='left')
                ttk.Label(frm, text=f"Error: {str(e)[:30]}...", foreground='red').pack(side='left')

            num = tk.Label(frm, text=str(idx), bg='yellow', font=('Arial', 8, 'bold'))
            num.place(in_=lbl, relx=0, rely=0)

            # hover effects
            for widget in (frm, lbl):
                widget.bind('<Enter>', lambda e, f=frm: f.config(style='Hover.TFrame'))
                widget.bind('<Leave>', lambda e, f=frm: f.config(style='TFrame'))

            btns = ttk.Frame(frm)
            btns.pack(side='right', padx=2)
            ttk.Button(btns, text='↑', width=2, command=lambda i=idx - 1: self.move(i, i - 1)).pack(pady=1)
            ttk.Button(btns, text='↓', width=2, command=lambda i=idx - 1: self.move(i, i + 1)).pack(pady=1)
            ttk.Button(btns, text='✕', width=2, command=lambda i=idx - 1: self.remove(i)).pack(pady=1)
            ttk.Button(btns, text='#', width=2, command=lambda i=idx - 1: self.set_pos(i)).pack(pady=1)

    def move(self, i, j):
        if 0 <= j < len(self.images): self.images.insert(j, self.images.pop(i)); self.refresh()

    def remove(self, i):
        del self.images[i];
        self.refresh()

    def set_pos(self, i):
        pos = simpledialog.askinteger('New Position', 'Enter new index:', initialvalue=i + 1, minvalue=1,
                                      maxvalue=len(self.images))
        if pos:
            item = self.images.pop(i);
            self.images.insert(pos - 1, item);
            self.refresh()

    def _on_click(self, event):
        y = event.y_root - self.inner.winfo_rooty()
        for idx, w in enumerate(self.inner.winfo_children()):
            if w.winfo_y() <= y <= w.winfo_y() + w.winfo_height():
                self._drag_idx = idx;
                self._drag_start_y = y;
                break

    def _on_drag(self, event):
        if self._drag_idx is None: return
        y = event.y_root - self.inner.winfo_rooty()
        widgets = self.inner.winfo_children()
        if widgets:
            target_idx = min(len(widgets) - 1, max(0, int(y / (widgets[0].winfo_height() + 4))))
            if target_idx != self._drag_idx:
                self.images.insert(target_idx, self.images.pop(self._drag_idx))
                self._drag_idx = target_idx
                self.refresh()

    def _on_release(self, event):
        self._drag_idx = None


def process_images(refs, tgts, outdir, prog, mask, tol):
    if len(refs) != len(tgts):
        messagebox.showerror("Error", f"Mismatch: {len(refs)} reference images vs {len(tgts)} target images")
        return

    n = len(refs);
    errs = []
    existing = [f for f in os.listdir(outdir) if 'AVGCOLOR' in f] if os.path.exists(outdir) else []
    if existing and not messagebox.askyesno('Overwrite',
                                            f'{len(existing)} existing output files found. Overwrite?'): return

    for i, (r, t) in enumerate(zip(refs, tgts)):
        prog.set((i + 1) / n * 100)
        try:
            a = Image.open(r).convert('RGB');
            b = Image.open(t).convert('RGB')
            avg_r = get_average_rgb(a, mask, tol);
            avg_b = get_average_rgb(b)
            res = shift_color(b, avg_r, avg_b)
            base, ext = os.path.splitext(os.path.basename(t))
            output_path = os.path.join(outdir, f"{base}_AVGCOLOR{ext}")
            res.save(output_path)
        except Exception as e:
            errs.append(f"Image {i + 1}: {str(e)}")

    prog.set(0)  # Reset progress bar
    if errs:
        messagebox.showwarning('Processing Complete with Errors',
                               f'Processed {n - len(errs)}/{n} images successfully.\n\nErrors:\n' + '\n'.join(
                                   errs[:5]) +
                               (f'\n... and {len(errs) - 5} more errors' if len(errs) > 5 else ''))
    else:
        messagebox.showinfo('Processing Complete', f'Successfully processed {n} images.')


def show_help():
    w = tk.Toplevel();
    w.title('Help - Color Match Tool')
    w.geometry('1000x700')
    txt = tk.Text(w, wrap='word', padx=10, pady=10)
    txt.insert('1.0',
               """Color Match Tool Help
               
               ADDING IMAGES:
               • Click "Add..." button to browse and select images
               • Drag & Drop: Drag image files directly from Explorer
               • Supported formats: PNG, JPG, JPEG, BMP, GIF, TIFF, WEBP
               
               ORGANIZING IMAGES:
                 ↑ ↓  - Move image up/down
                 ✕    - Remove image (with confirmation)
                 #    - Set specific position manually
               • Drag thumbnails up/down to reorder directly
               • Yellow number shows current position
               
               
               MASK COLOR & TOLERANCE:
               • Default Mask Color [0,0,0] ignores pure black pixels
               • Tolerance defines similarity threshold:
                 - 0: Only exact mask color excluded
                 - 10: Pixels within ±10 in each RGB channel excluded
                 - Higher values exclude more similar colors
               • Use tolerance > 0 if your "empty" areas aren't perfectly black
               
               PROCESSING:
               • Reference and Target pools must have same number of images
               • Each target[i] is matched to reference[i] in order
               • Output files saved as: <targetname>_AVGCOLOR<extension>
               • Progress bar shows processing status
               • Confirmation dialog if output files already exist
               
               TIPS:
               • Use Clear button to remove all images from a pool
               • Image info shows filename and dimensions
               • Error thumbnails (❌) indicate corrupted/unsupported files
               """
               )
    txt.config(state='disabled')
    txt.pack(fill='both', expand=True)

    # Add close button
    ttk.Button(w, text='Close', command=w.destroy).pack(pady=10)


def run_gui():
    load_settings()

    # Use TkinterDnD if available, otherwise regular Tk
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    root.title('Match Average Color')
    root.geometry('1200x800')
    root.minsize(800, 600)

    # Configure styles
    style = ttk.Style()
    try:
        style.configure('Hover.TFrame', background='#f0f8ff')
    except:
        pass

    main = ttk.Frame(root)
    main.pack(fill='both', expand=True, padx=10, pady=5)

    # Create image pools
    pool_r = ImagePool(main, 'Reference Images', 'last_ref_dir')
    pool_t = ImagePool(main, 'Target Images', 'last_tgt_dir')
    pool_r.pack(side='left', fill='both', expand=True, padx=(0, 5))
    pool_t.pack(side='right', fill='both', expand=True, padx=(5, 0))

    # Control panel
    ctrl = ttk.LabelFrame(root, text='Processing Options', padding=10)
    ctrl.pack(fill='x', padx=10, pady=5)

    # Settings row
    settings_frame = ttk.Frame(ctrl)
    settings_frame.pack(fill='x', pady=5)

    ttk.Label(settings_frame, text='Mask Color (R,G,B):').pack(side='left')
    ent = ttk.Entry(settings_frame, width=12)
    ent.insert(0, ','.join(map(str, settings['mask_color'])))
    ent.pack(side='left', padx=(5, 15))

    ttk.Label(settings_frame, text='Tolerance:').pack(side='left')
    sp = ttk.Spinbox(settings_frame, from_=0, to=255, width=8)
    sp.set(settings['mask_tolerance'])
    sp.pack(side='left', padx=(5, 15))

    ttk.Button(settings_frame, text='Help', command=show_help).pack(side='left', padx=10)

    # Status and progress
    status_frame = ttk.Frame(ctrl)
    status_frame.pack(fill='x', pady=5)

    status_var = tk.StringVar(value="Ready")
    ttk.Label(status_frame, textvariable=status_var).pack(side='left')

    prog = tk.DoubleVar()
    progress_bar = ttk.Progressbar(status_frame, variable=prog, length=300)
    progress_bar.pack(side='right', padx=10)

    def update_status():
        ref_count = len(pool_r.images)
        tgt_count = len(pool_t.images)
        status_var.set(f"Reference: {ref_count} images | Target: {tgt_count} images | " +
                       ("Ready to process" if ref_count == tgt_count and ref_count > 0
                        else "Add images to both pools" if ref_count == 0 or tgt_count == 0
                       else f"Image count mismatch ({ref_count} vs {tgt_count})"))
        root.after(1000, update_status)

    update_status()

    def go():
        if not pool_r.images or not pool_t.images:
            messagebox.showwarning("No Images", "Please add images to both pools")
            return

        if len(pool_r.images) != len(pool_t.images):
            messagebox.showerror("Image Count Mismatch",
                                 f"Reference pool has {len(pool_r.images)} images but target pool has {len(pool_t.images)} images.\n" +
                                 "Both pools must have the same number of images.")
            return

        out = filedialog.askdirectory(title='Select Output Directory', initialdir=settings['last_out_dir'])
        if not out:
            return

        settings['last_out_dir'] = out

        try:
            mask = list(map(int, ent.get().replace(' ', '').split(',')))
            if len(mask) != 3:
                raise ValueError("Mask color must have exactly 3 values")
            settings['mask_color'] = mask
        except ValueError as e:
            messagebox.showerror("Invalid Mask Color",
                                 f"Please enter mask color as three comma-separated integers (0-255)\nError: {e}")
            return

        try:
            tol = int(sp.get())
            settings['mask_tolerance'] = tol
        except ValueError:
            messagebox.showerror("Invalid Tolerance", "Please enter a valid tolerance value (0-255)")
            return

        save_settings()
        process_images(pool_r.images, pool_t.images, out, prog, mask, tol)

    # Process button
    process_frame = ttk.Frame(root)
    process_frame.pack(fill='x', padx=10, pady=10)
    ttk.Button(process_frame, text='🎨 Process Images', command=go, style='Accent.TButton').pack(side='right')

    # Show drag & drop status
    if DND_AVAILABLE:
        ttk.Label(process_frame, text='✅ Drag & Drop enabled', foreground='green', font=('Arial', 8)).pack(side='left')
    else:
        ttk.Label(process_frame, text='⚠️ Drag & Drop not available (install tkinterdnd2)', foreground='orange',
                  font=('Arial', 8)).pack(side='left')

    root.mainloop()


if __name__ == '__main__':
    run_gui()