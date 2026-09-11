import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import threading
import windnd
from encryption import encrypt_file
from s3_uploader import upload_to_s3

class S3DriveApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("S3Drive Replica - Secure Uploader [v0.1.7]")
        self.geometry("600x800")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # UI State
        self.selected_files = []
        self.is_uploading = False
        self.log_file_path = "app_log.txt"

        # --- UI LAYOUT ---
        self.grid_columnconfigure(0, weight=1)

        # Connection Frame
        self.conn_frame = ctk.CTkFrame(self)
        self.conn_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(self.conn_frame, text="AWS S3 Connection", font=("Arial", 16, "bold")).pack(pady=5)
        
        self.access_key = self.create_input(self.conn_frame, "AWS Access Key")
        self.secret_key = self.create_input(self.conn_frame, "AWS Secret Key", show="*")
        self.bucket_name = self.create_input(self.conn_frame, "Bucket Name")
        self.region = self.create_input(self.conn_frame, "Region (e.g. us-east-1)")

        # Security Frame
        self.sec_frame = ctk.CTkFrame(self)
        self.sec_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(self.sec_frame, text="PGP Encryption", font=("Arial", 16, "bold")).pack(pady=5)
        
        self.enc_mode = ctk.CTkSegmentedButton(self.sec_frame, values=["Symmetric", "Hybrid (Public Key)"])
        self.enc_mode.set("Symmetric")
        self.enc_mode.pack(pady=5)

        self.key_input = ctk.CTkTextbox(self.sec_frame, height=100)
        self.key_input.pack(pady=10, padx=10, fill="x")
        self.key_input.insert("1.0", "Enter Passphrase or Public Key here...")

        # Upload Frame
        self.up_frame = ctk.CTkFrame(self)
        self.up_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(self.up_frame, text="Files to Upload", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Improved File List (Scrollable)
        self.file_list_frame = ctk.CTkScrollableFrame(self.up_frame, height=150)
        self.file_list_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.btn_select = ctk.CTkButton(self.up_frame, text="Select Files", command=self.select_files)
        self.btn_select.pack(pady=5)
        
        self.btn_clear = ctk.CTkButton(self.up_frame, text="Clear List", fg_color="gray", command=self.clear_files)
        self.btn_clear.pack(pady=5)

        # ACTION BUTTON
        self.btn_upload = ctk.CTkButton(self, text="ENCRYPT & UPLOAD", fg_color="green", 
                                       hover_color="darkgreen", command=self.start_upload_thread, font=("Arial", 14, "bold"))
        self.btn_upload.pack(pady=20)

        # Log Window
        ctk.CTkLabel(self, text="Activity Log", font=("Arial", 12, "bold")).pack(pady=(10, 0))
        self.log = ctk.CTkTextbox(self, height=180)
        self.log.pack(pady=10, padx=20, fill="x")
        self.write_log("Ready to upload! ✨")

        # --- Drag and Drop Setup ---
        # Use windnd to hook into the Windows window handle (winfo_id() is the HWND)
        windnd.hook_dropfiles(self.winfo_id(), self.handle_drop)

    def create_input(self, parent, label, show=None):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(pady=5, padx=10, fill="x")
        ctk.CTkLabel(frame, text=label, width=120, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(frame, show=show)
        entry.pack(side="right", fill="x", expand=True)
        return entry

    def write_log(self, text):
        self.after(0, lambda: self._do_write_log(text))
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(f"{text}\n")
        except:
            pass

    def _do_write_log(self, text):
        self.log.insert("end", f"{text}\n")
        self.log.see("end")

    def update_file_list_ui(self):
        # Clear the scrollable frame
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        
        # Add each file as a label
        for i, path in enumerate(self.selected_files):
            filename = os.path.basename(path)
            lbl = ctk.CTkLabel(self.file_list_frame, text=f"{i+1}. {filename}", font=("Arial", 12))
            lbl.pack(anchor="w", padx=10, pady=2)

    def select_files(self):
        files = filedialog.askopenfilenames()
        if files:
            # Add to existing list instead of replacing
            for f in files:
                if f not in self.selected_files:
                    self.selected_files.append(f)
            self.update_file_list_ui()
            self.write_log(f"Added {len(files)} file(s). 📂")

    def handle_drop(self, files):
        # windnd provides files as a list of bytes/strings
        # We need to decode them and clean up any curly braces (Windows paths with spaces)
        dropped_files = []
        for f in files:
            # Decode if it's bytes
            path = f.decode('utf-8') if isinstance(f, bytes) else f
            # Remove curly braces that windnd sometimes adds to paths with spaces
            if path.startswith('{') and path.endswith('}'):
                path = path[1:-1]
            
            if os.path.exists(path) and path not in self.selected_files:
                self.selected_files.append(path)
                dropped_files.append(path)
        
        self.after(0, self.update_file_list_ui)
        self.after(0, lambda: self.write_log(f"Dropped {len(dropped_files)} file(s). 📥"))

    def clear_files(self):
        self.selected_files = []
        self.update_file_list_ui()
        self.write_log("File list cleared. 🧹")

    def start_upload_thread(self):
        if self.is_uploading:
            return
        self.log.delete("1.0", "end")
        self.write_log("Starting new upload process... 🚀")
        thread = threading.Thread(target=self.process_upload, daemon=True)
        thread.start()

    def process_upload(self):
        self.is_uploading = True
        self.after(0, lambda: self.btn_upload.configure(state="disabled", text="Uploading... 🚀"))

        access = self.access_key.get()
        secret = self.secret_key.get()
        bucket = self.bucket_name.get()
        region = self.region.get()
        key_data = self.key_input.get("1.0", "end-1c").strip()

        if not all([access, secret, bucket, region, key_data]):
            self.after(0, lambda: messagebox.showerror("Error", "Please fill in all connection and encryption details!"))
            self.finalize_upload()
            return

        if not self.selected_files:
            self.after(0, lambda: messagebox.showerror("Error", "Please select at least one file!"))
            self.finalize_upload()
            return

        mode = self.enc_mode.get()
        success_count = 0
        fail_count = 0
        
        # Copy list to avoid modification issues during iteration
        files_to_process = list(self.selected_files)
        
        for file_path in files_to_process:
            filename = os.path.basename(file_path)
            try:
                self.write_log(f"Processing {filename}... ✨")
                
                if mode == "Symmetric":
                    encrypted_content = encrypt_file(file_path, passphrase=key_data)
                else:
                    if mode == "Hybrid (Public Key)":
                        self.write_log(f"Generating random session key... 🔑")
                        self.write_log(f"Encrypting {filename} with session key... 🔐")
                        self.write_log(f"Encrypting session key with Public Key... 🔒")
                    encrypted_content = encrypt_file(file_path, public_key=key_data)
                
                self.write_log(f"Encryption complete! 🛡️")

                obj_name = filename + ".pgp"
                success, msg = upload_to_s3(encrypted_content, bucket, obj_name, access, secret, region)
                
                if success:
                    self.write_log(f"Uploaded {obj_name} to S3. 🚀")
                    self.write_log(f"Verification: {msg} ✅")
                    
                    # Local file is kept for safety (as per v0.1.4)
                    self.write_log(f"Local file {filename} has been kept. ✨")
                    success_count += 1
                else:
                    self.write_log(f"Upload/Verification failed for {filename}: {msg} ❌")
                    self.write_log(f"Local file {filename} has been KEPT for safety! 🛡️")
                    fail_count += 1

            except Exception as e:
                self.write_log(f"Error processing {filename}: {str(e)} ❌")
                fail_count += 1

        summary = f"Process completed!\n\n✅ Verified: {success_count}\n❌ Failed: {fail_count}\n\nBucket: {bucket}\nRegion: {region}"
        self.after(0, lambda: messagebox.showinfo("Finished", summary))
        
        self.selected_files = []
        self.after(0, self.update_file_list_ui)
        self.finalize_upload()

    def finalize_upload(self):
        self.is_uploading = False
        self.after(0, lambda: self.btn_upload.configure(state="normal", text="ENCRYPT & UPLOAD"))

if __name__ == "__main__":
    app = S3DriveApp()
    app.mainloop()
