# ####################################################################
#
#   FINAL PYINSTALLER VERSION
#
#   This version uses sys._MEIPASS to correctly locate bundled
#   data files within a PyInstaller app. It contains NO other
#   special path manipulation.
#
# ####################################################################

import sys
import os
import platform

# --- PYINSTALLER PATH FIX ---
# This block runs only when the app is a frozen PyInstaller bundle.
if getattr(sys, 'frozen', False):
    # sys._MEIPASS is a temporary directory created by PyInstaller at runtime.
    # It contains all the bundled files.
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    
    # Tell Playwright where to find the browser folder we will manually copy.
    # The path must match the destination in our build script.
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.join(base_path, 'ms-playwright')

# --- Now, it's safe to import everything else ---
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import markdown
import tempfile
import subprocess
from PIL import Image
import re
import asyncio
import threading
import io
from playwright.async_api import async_playwright

# ####################################################################
# YOUR APPLICATION CLASS - MODIFIED
# ####################################################################
class PlaywrightMathConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("markdown2png")
        self.root.geometry("1200x800")
        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        title_label = ttk.Label(main_frame, text="Paste your markdown below (or use clipboard buttons):", font=('Arial', 16))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10), sticky=tk.W)
        self.input_text = scrolledtext.ScrolledText(main_frame, width=60, height=25, wrap=tk.WORD, font=('Courier', 11))
        self.input_text.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=2, sticky=(tk.N, tk.W), padx=(10, 0))
        ttk.Label(control_frame, text="Image Width (px):").grid(row=0, column=0, sticky=tk.W, pady=(5,0))
        self.width = tk.IntVar(value=800)
        ttk.Spinbox(control_frame, from_=600, to=1600, textvariable=self.width, width=15).grid(row=1, column=0, sticky=tk.W)
        ttk.Label(control_frame, text="Resolution Scale (DPI):").grid(row=2, column=0, sticky=tk.W, pady=(5,0))
        self.scale = tk.IntVar(value=4)
        ttk.Spinbox(control_frame, from_=1, to=5, textvariable=self.scale, width=15).grid(row=3, column=0, sticky=tk.W)
        ttk.Label(control_frame, text="Base Font Size (px):").grid(row=4, column=0, sticky=tk.W, pady=(5,0))
        self.font_size = tk.IntVar(value=18)
        ttk.Spinbox(control_frame, from_=12, to=24, textvariable=self.font_size, width=15).grid(row=5, column=0, sticky=tk.W)
        ttk.Label(control_frame, text="Theme:").grid(row=6, column=0, sticky=tk.W, pady=(5,0))
        self.theme = tk.StringVar(value="Academic")
        ttk.Combobox(control_frame, textvariable=self.theme, values=["Academic", "GitHub", "Clean"], state="readonly", width=13).grid(row=7, column=0, pady=(0, 15))
        
        ttk.Button(control_frame, text="Copy to Clipboard", command=self.copy_to_clipboard).grid(row=8, column=0, pady=2, sticky='ew')
        ttk.Button(control_frame, text="Save as PNG", command=self.save_png).grid(row=9, column=0, pady=2, sticky='ew')
        ttk.Button(control_frame, text="Preview HTML", command=self.preview_html).grid(row=10, column=0, pady=2, sticky='ew')
        ttk.Button(control_frame, text="Clear", command=self.clear_input).grid(row=11, column=0, pady=(10, 0), sticky='ew')
        
        # --- NEW WIDGET ---
        ttk.Separator(control_frame, orient='horizontal').grid(row=12, column=0, sticky='ew', pady=10)
        ttk.Button(control_frame, text="Clipboard → Clipboard", command=self.process_clipboard_to_clipboard).grid(row=13, column=0, pady=2, sticky='ew')
        # --- END NEW WIDGET ---
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        self.input_text.insert('1.0', "")

    def get_css_styles(self):
        base_font_size, width, theme = self.font_size.get(), self.width.get(), self.theme.get()
        themes = { "Academic": f"@import url('https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,700;1,400&display=swap'); body {{ font-family: 'Crimson Text', 'Georgia', serif; font-size: {base_font_size}px; line-height: 1.7; max-width: {width - 100}px; margin: auto; padding: 50px; background: white; color: #2c3e50; }}", "GitHub": f"body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: {base_font_size}px; line-height: 1.6; max-width: {width - 80}px; margin: auto; padding: 40px; background: white; color: #24292f; }}", "Clean": f"body {{ font-family: 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif; font-size: {base_font_size}px; line-height: 1.6; max-width: {width - 100}px; margin: auto; padding: 50px; background: white; color: #333; }}"}
        return themes.get(theme, themes["Academic"])

    def markdown_to_html(self, markdown_text):
        math_stash = []
        def stash_display_math(m):
            math_stash.append(m.group(0))
            return f"<!--MATH_BLOCK_{len(math_stash)-1}-->"
        def stash_inline_math(m):
            math_stash.append(m.group(0))
            return f"<!--MATH_BLOCK_{len(math_stash)-1}-->"
        stashed_text = re.sub(r'\$\$[\s\S]+?\$\$', stash_display_math, markdown_text)
        stashed_text = re.sub(r'\$[^\$]+?\$', stash_inline_math, stashed_text)
        html_body = markdown.Markdown(extensions=['extra', 'tables', 'fenced_code']).convert(stashed_text)
        for i, math_block in enumerate(math_stash):
            placeholder = f"<!--MATH_BLOCK_{i}-->"
            if math_block.startswith("$$"):
                html_body = html_body.replace(placeholder, f"<div>{math_block}</div>")
            else:
                html_body = html_body.replace(placeholder, f"<span>{math_block}</span>")
        html = f"""
            <!DOCTYPE html><html><head><meta charset="utf-8">
            <style>{self.get_css_styles()}</style>
            <script>
                window.mathjaxIsReady = new Promise(resolve => {{
                    window.MathJax = {{
                        tex: {{ inlineMath: [['$', '$']], displayMath: [['$$', '$$']] }},
                        startup: {{ pageReady: () => {{ return MathJax.startup.defaultPageReady().then(resolve); }} }}
                    }};
                }});
            </script>
            <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
            </head><body>{html_body}</body></html>
        """
        return html

    # --- NEW HELPER METHOD ---
    def _populate_from_clipboard_if_empty(self):
        """Checks if the input text is empty. If so, tries to fill it from the clipboard."""
        if not self.input_text.get('1.0', tk.END).strip():
            try:
                clipboard_content = self.root.clipboard_get()
                if clipboard_content:
                    self.input_text.insert('1.0', clipboard_content)
                    self.status_var.set("Pasted content from clipboard.")
            except tk.TclError:
                # This error occurs if the clipboard is empty or contains non-text data
                pass

    # --- MODIFIED METHOD ---
    def _start_threaded_conversion(self, on_success):
        self._populate_from_clipboard_if_empty()
        
        text = self.input_text.get('1.0', tk.END).strip()
        if not text:
            messagebox.showwarning("Input Missing", "Please enter some text or copy it to your clipboard.")
            self.status_var.set("Ready")
            return
            
        self.status_var.set("Generating HTML...")
        html_content = self.markdown_to_html(text)
        def run_in_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self.status_var.set(f"Rendering content at {self.scale.get()}x scale...")
                async def convert_task():
                    async with async_playwright() as p:
                        browser = await p.chromium.launch()
                        page = await browser.new_page(device_scale_factor=self.scale.get())
                        await page.set_viewport_size({"width": self.width.get(), "height": 100})
                        await page.set_content(html_content, wait_until="domcontentloaded")
                        await page.evaluate("window.mathjaxIsReady")
                        screenshot_bytes = await page.screenshot(full_page=True, type='png')
                        await browser.close()
                        return Image.open(io.BytesIO(screenshot_bytes))
                image_result = loop.run_until_complete(convert_task())
                self.root.after(0, on_success, image_result)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Conversion Error", str(e)))
                self.root.after(0, lambda: self.status_var.set("Error during conversion."))
        threading.Thread(target=run_in_thread, daemon=True).start()

    def copy_to_clipboard(self):
        if platform.system() != 'Darwin':
            messagebox.showerror("Unsupported OS", "This copy function is for macOS.")
            return
        def _perform_copy(image):
            self.status_var.set("Copying to clipboard...")
            tmp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    tmp_file_path = tmp.name
                image.save(tmp_file_path, 'PNG')
                subprocess.run(['osascript', '-e', f'set the clipboard to (read (POSIX file "{tmp_file_path}") as TIFF picture)'], check=True)
                self.status_var.set("Image copied to clipboard!")
            except Exception as e:
                messagebox.showerror("Clipboard Error", f"Failed to copy image to clipboard.\n\nError: {e}")
            finally:
                if tmp_file_path and os.path.exists(tmp_file_path): os.remove(tmp_file_path)
        self._start_threaded_conversion(on_success=_perform_copy)

    def save_png(self):
        def _perform_save(image):
            file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
            if file_path:
                self.status_var.set("Saving image...")
                dpi_val = self.scale.get() * 96 
                image.save(file_path, 'PNG', dpi=(dpi_val, dpi_val))
                self.status_var.set(f"Image saved to: {os.path.basename(file_path)}")
            else: self.status_var.set("Save cancelled.")
        self._start_threaded_conversion(on_success=_perform_save)
    
    # --- MODIFIED METHOD ---
    def preview_html(self):
        self._populate_from_clipboard_if_empty()
        text = self.input_text.get('1.0', tk.END).strip()
        if not text:
            messagebox.showwarning("Input Missing", "Please enter some text or copy it to your clipboard.")
            self.status_var.set("Ready")
            return
            
        html_content = self.markdown_to_html(text)
        with tempfile.NamedTemporaryFile('w', delete=False, suffix=".html", encoding='utf-8') as f:
            temp_path = f.name
            f.write(html_content)
        if platform.system() == 'Darwin': subprocess.run(['open', temp_path], check=True)
        else:
            try: os.startfile(temp_path)
            except AttributeError: subprocess.run(['xdg-open', temp_path], check=True)
        self.status_var.set("HTML preview opened in browser.")

    def clear_input(self):
        self.input_text.delete('1.0', tk.END)
        self.status_var.set("Ready")

    # --- NEW METHOD ---
    def process_clipboard_to_clipboard(self):
        """Clears the text area, then triggers the clipboard copy process, which
           will automatically pull from the system clipboard."""
        self.input_text.delete('1.0', tk.END) # Clear first to ensure it pulls from clipboard
        self.copy_to_clipboard()

# ####################################################################
#   MAIN EXECUTION BLOCK
# ####################################################################
if __name__ == "__main__":
    root = tk.Tk()
    app = PlaywrightMathConverter(root)
    root.mainloop()