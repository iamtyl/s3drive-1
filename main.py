import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import threading
import json
import sys
import windnd
from encryption import encrypt_file
from s3_uploader import upload_to_s3

class S3DriveApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("S3Drive Replica - Secure Uploader [v0.1.11]")
        self.geometry("600x800")
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # UI State
        self.selected_files = []
        self.is_uploading = False
        
        # --- PERMANENT CONFIG STORAGE ---
        # Using %APPDATA% ensures settings are saved in a user-accessible folder 
        # and won't be lost when the .exe is run from a temporary directory.
        self.app_data_dir = os.path.join(os.getenv('APPDATA', os.path.expanduser('~')), "S3DriveReplica")
        os.makedirs(self.app_data_dir, exist_ok=True)
        
        self.config_file = os.path.join(self.app_data_dir, "config.json")
        self.log_file_path = os.path.join(self.app_data_dir, "app_log.txt")

        # --- UI LAYOUT ---
        self.main_container = ctk.CTkScrollableFrame(self)
        self.main_container.pack(pady=0, padx=0, fill="both", expand=True)
        
        # Connection Frame
        self.conn_frame = ctk.CTkFrame(self.main_container)
        self.conn_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(self.conn_frame, text="AWS S3 Connection", font=("Arial", 16, "bold")).pack(pady=5)
        
        self.access_key = self.create_input(self.conn_frame, "AWS Access Key")
        self.secret_key = self.create_input(self.conn_frame, "AWS Secret Key", show="*")
        self.bucket_name = self.create_input(self.conn_frame, "Bucket Name")
        self.region = self.create_input(self.conn_frame, "Region (e.g. us-east-1)")

        # Security Frame
        self.sec_frame = ctk.CTkFrame(self.main_container)
        self.sec_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(self.sec_frame, text="PGP Encryption", font=("Arial", 16, "bold")).pack(pady=5)
        
        self.enc_mode = ctk.CTkSegmentedButton(self.sec_frame, values=["Symmetric", "Hybrid (Public Key)"])
        self.enc_mode.set("Symmetric")
        self.enc_mode.pack(pady=5)

        self.key_input = ctk.CTkTextbox(self.sec_frame, height=100)
        self.key_input.pack(pady=10, padx=10, fill="x")
        self.key_input.insert("1.0", "Enter Passphrase or Public Key here...")

        # Upload Frame
        self.up_frame = ctk.CTkFrame(self.main_container)
        self.up_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(self.up_frame, text="Files to Upload", font=("Arial", 14, "bold")).pack(pady=5)
        
        self.file_list_frame = ctk.CTkScrollableFrame(self.up_frame, height=150)
        self.file_list_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.btn_select = ctk.CTkButton(self.up_frame, text="Select Files", command=self.select_files)
        self.btn_select.pack(pady=5)
        
        self.btn_clear = ctk.CTkButton(self.up_frame, text="Clear List", fg_color="gray", command=self.clear_files)
        self.btn_clear.pack(pady=5)

        # ACTION BUTTON
        self.btn_upload = ctk.CTkButton(self.main_container, text="ENCRYPT & UPLOAD", fg_color="green", 
                                       hover_color="darkgreen", command=self.start_upload_thread, font=("Arial", 14, "bold"))
        self.btn_upload.pack(pady=20)

        # Log Window
        ctk.CTkLabel(self.main_container, text="Activity Log", font=("Arial", 12, "bold")).pack(pady=(10, 0))
        self.log = ctk.CTkTextbox(self.main_container, height=180)
        self.log.pack(pady=10, padx=20, fill="x")
        self.write_log("Ready to upload! ✨")

        # Load saved config
        self.load_config()

        # --- Drag and Drop Setup ---
        # Using a delay to ensure the window is fully realized in Windows memory
        self.after(500, self.setup_drag_and_drop)

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

    def setup_drag_and_drop(self):
        try:
            # Try to hook using the instance itself first (most stable for some CTK versions)
            windnd.hook_dropfiles(self, self.handle_drop)
            self.write_log("Drag and drop system enabled. 📥")
        except Exception as e:
            try:
                # Fallback to winfo_id
                windnd.hook_dropfiles(self.winfo_id(), self.handle_drop)
                self.write_log("Drag and drop system enabled (ID mode). 📥")
            except Exception as e2:
                self.write_log(f"Critical: Drag and drop failed to initialize: {str(e2)} ❌")

    def update_file_list_ui(self):
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        for i, path in enumerate(self.selected_files):
            filename = os.path.basename(path)
            lbl = ctk.CTkLabel(self.file_list_frame, text=f"{i+1}. {filename}", font=("Arial", 12))
            lbl.pack(anchor="w", padx=10, pady=2)

    def select_files(self):
        files = filedialog.askopenfilenames()
        if files:
            for f in files:
                if f not in self.selected_files:
                    self.selected_files.append(f)
            self.update_file_list_ui()
            self.write_log(f"Added {len(files)} file(s). 📂")

    def handle_drop(self, files):
        # windnd calls this from a separate OS thread. 
        # We MUST move all GUI logic into self.after(0, ...) immediately.
        def process_drop():
            dropped_files = []
            for f in files:
                path = f.decode('utf-8') if isinstance(f, bytes) else f
                if path.startswith('{') and path.endswith('}'):
                    path = path[1:-1]
                if os.path.exists(path) and path not in self.selected_files:
                    self.selected_files.append(path)
                    dropped_files.append(path)
            self.update_file_list_ui()
            self.write_log(f"Dropped {len(dropped_files)} file(s). 📥")

        self.after(0, process_drop)

    def clear_files(self):
        self.selected_files = []
        self.update_file_list_ui()
        self.write_log("File list cleared. 🧹")

    def save_config(self):
        config = {
            "access_key": self.access_key.get(),
            "bucket_name": self.bucket_name.get(),
            "region": self.region.get(),
            "enc_mode": self.enc_mode.get(),
            "key_data": self.key_input.get("1.0", "end-1c").strip()
        }
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                self.access_key.insert(0, config.get("access_key", ""))
                self.bucket_name.insert(0, config.get("bucket_name", ""))
                self.region.insert(0, config.get("region", ""))
                self.enc_mode.set(config.get("enc_mode", "Symmetric"))
                self.key_input.delete("1.0", "end")
                self.key_input.insert("1.0", config.get("key_data", ""))
            except Exception as e:
                print(f"Failed to load config: {e}")

    def start_upload_thread(self):
        if self.is_uploading:
            return
        self.save_config()
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
