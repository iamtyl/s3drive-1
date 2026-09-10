
import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
from encryption import encrypt_file
from s3_uploader import upload_to_s3

class S3DriveApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("S3Drive Replica - Secure Uploader")
        self.geometry("600x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # UI State
        self.selected_files = []

        # --- UI LAYOUT ---
        self.grid_columnconfigure(0, weight=1)

        # Connection Frame
        self.conn_frame = ctk.CTkFrame(self)
        self.conn_frame.pack(pady=20, padx=20, fill="x")
        
        ctk.CTkLabel(self.conn_frame, text="AWS S3 Connection", font=("Arial", 16, "bold")).pack(pady=5)
        
        self.access_key = self.create_input(self.conn_frame, "AWS Access Key")
        self.secret_key = self.create_input(self.conn_frame, "AWS Secret Key", show="*")
        self.bucket_name = self.create_input(self.conn_frame, "Bucket Name")
        self.region = self.create_input(self.conn_frame, "Region (e.g. us-east-1)")

        # Security Frame
        self.sec_frame = ctk.CTkFrame(self)
        self.sec_frame.pack(pady=20, padx=20, fill="x")
        
        ctk.CTkLabel(self.sec_frame, text="PGP Encryption", font=("Arial", 16, "bold")).pack(pady=5)
        
        self.enc_mode = ctk.CTkSegmentedButton(self.sec_frame, values=["Symmetric", "Asymmetric"])
        self.enc_mode.set("Symmetric")
        self.enc_mode.pack(pady=5)

        self.key_input = ctk.CTkTextbox(self.sec_frame, height=100)
        self.key_input.pack(pady=10, padx=10, fill="x")
        self.key_input.insert("1.0", "Enter Passphrase or Public Key here...")

        # Upload Frame
        self.up_frame = ctk.CTkFrame(self)
        self.up_frame.pack(pady=20, padx=20, fill="x")

        self.file_label = ctk.CTkLabel(self.up_frame, text="No files selected")
        self.file_label.pack(pady=10)

        self.btn_select = ctk.CTkButton(self.up_frame, text="Select Files", command=self.select_files)
        self.btn_select.pack(pady=5)

        self.btn_upload = ctk.CTkButton(self, text="ENCRYPT & UPLOAD", fg_color="green", 
                                       hover_color="darkgreen", command=self.process_upload, font=("Arial", 14, "bold"))
        self.btn_upload.pack(pady=30)

        # Log
        self.log = ctk.CTkTextbox(self, height=150)
        self.log.pack(pady=10, padx=20, fill="x")
        self.write_log("Ready to upload! ✨")

    def create_input(self, parent, label, show=None):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(pady=5, padx=10, fill="x")
        ctk.CTkLabel(frame, text=label, width=120, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(frame, show=show)
        entry.pack(side="right", fill="x", expand=True)
        return entry

    def write_log(self, text):
        self.log.insert("end", f"{text}\n")
        self.log.see("end")

    def select_files(self):
        files = filedialog.askopenfilenames()
        if files:
            self.selected_files = list(files)
            self.file_label.configure(text=f"{len(files)} file(s) selected")
            self.write_log(f"Selected {len(files)} files. 📂")

    def process_upload(self):
        # Validation
        access = self.access_key.get()
        secret = self.secret_key.get()
        bucket = self.bucket_name.get()
        region = self.region.get()
        key_data = self.key_input.get("1.0", "end-1c").strip()

        if not all([access, secret, bucket, region, key_data]):
            messagebox.showerror("Error", "Please fill in all connection and encryption details!")
            return

        if not self.selected_files:
            messagebox.showerror("Error", "Please select at least one file!")
            return

        mode = self.enc_mode.get()
        
        for file_path in self.selected_files:
            filename = os.path.basename(file_path)
            try:
                self.write_log(f"Processing {filename}... ✨")
                
                # 1. Encrypt
                if mode == "Symmetric":
                    encrypted_content = encrypt_file(file_path, passphrase=key_data)
                else:
                    encrypted_content = encrypt_file(file_path, public_key=key_data)
                
                self.write_log(f"Encrypted {filename} locally. 🔐")

                # 2. Upload
                obj_name = filename + ".pgp"
                success, msg = upload_to_s3(encrypted_content, bucket, obj_name, access, secret, region)
                
                if success:
                    self.write_log(f"Uploaded {obj_name} to S3. 🚀")
                    
                    # 3. Remove Local File
                    os.remove(file_path)
                    self.write_log(f"Deleted local file {filename}. 🧹")
                else:
                    self.write_log(f"Upload failed for {filename}: {msg} ❌")

            except Exception as e:
                self.write_log(f"Error processing {filename}: {str(e)} ❌")

        self.selected_files = []
        self.file_label.configure(text="No files selected")
        messagebox.showinfo("Finished", "Upload process completed!")

if __name__ == "__main__":
    app = S3DriveApp()
    app.mainloop()
