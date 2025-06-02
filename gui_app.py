import os
import sys
import traceback
import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

try:
    from cams_parser import extract_transactions_from_pdf, convert_to_csv_string
except ImportError:
    messagebox.showerror(
        "Import Error",
        "Could not import 'cams_parser.py'. Make sure it's in the same directory.",
    )
    sys.exit()


class CAMSProcessorApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("CAMS PDF Statement Processor")
        self.setup_window_geometry("800x600")  # Increased window size
        self.root.resizable(True, True)

        # Configure grid weights for responsive design
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Variables
        self.selected_file = ctk.StringVar()
        self.password = ctk.StringVar()
        self.status_text = ctk.StringVar(value="Ready to process PDF statements")

        # Output directory setup
        if getattr(sys, "frozen", False):
            self.application_path = os.path.dirname(sys.executable)
        else:
            self.application_path = os.path.dirname(__file__)

        self.GENERATED_CSVS_FOLDER = os.path.join(
            self.application_path, "generated_csvs"
        )
        os.makedirs(self.GENERATED_CSVS_FOLDER, exist_ok=True)

        # Create GUI elements
        self.create_widgets()

    def setup_window_geometry(self, geometry_string):
        """Center the window on the screen"""
        # Get the geometry dimensions
        width, height = map(int, geometry_string.split("x"))

        # Get the screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Calculate center position
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        # Set the geometry
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def create_widgets(self):
        # Main container with padding
        main_frame = ctk.CTkFrame(self.root, corner_radius=20, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=30, pady=30)
        main_frame.grid_columnconfigure(0, weight=1)

        # Header section
        header_frame = ctk.CTkFrame(main_frame, corner_radius=15, height=100)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 30))
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_propagate(False)

        # App title with icon
        title_label = ctk.CTkLabel(
            header_frame,
            text="📊 CAMS PDF Statement Processor",
            font=ctk.CTkFont(size=24, weight="bold"),  # Reduced from 28
            text_color=("gray10", "gray90"),
        )
        title_label.grid(row=0, column=0, pady=15)  # Reduced padding

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Convert your CAMS PDF statements to CSV format",
            font=ctk.CTkFont(size=13),  # Reduced from 14
            text_color=("gray40", "gray60"),
        )
        subtitle_label.grid(row=1, column=0, pady=(0, 15))  # Reduced padding

        # Content area
        content_frame = ctk.CTkFrame(main_frame, corner_radius=15)
        content_frame.grid(
            row=1, column=0, sticky="nsew", pady=(0, 15)
        )  # Reduced padding
        content_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        # File selection section
        file_section_label = ctk.CTkLabel(
            content_frame,
            text="📁 Select PDF Statement",
            font=ctk.CTkFont(size=16, weight="bold"),  # Reduced from 18
            anchor="w",
        )
        file_section_label.grid(
            row=0, column=0, columnspan=3, sticky="w", padx=30, pady=(20, 10)
        )  # Adjusted padding

        # File path display
        self.file_entry = ctk.CTkEntry(
            content_frame,
            textvariable=self.selected_file,
            placeholder_text="No file selected...",
            height=40,  # Reduced from 45
            font=ctk.CTkFont(size=13),  # Increased from 12
            corner_radius=8,
        )
        self.file_entry.grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=(30, 10), pady=(0, 15)
        )

        # Browse button
        browse_button = ctk.CTkButton(
            content_frame,
            text="Browse",
            command=self.browse_file,
            width=100,
            height=45,
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=10,
        )
        browse_button.grid(row=1, column=2, sticky="e", padx=(0, 30), pady=(0, 15))

        # Password section
        password_section_label = ctk.CTkLabel(
            content_frame,
            text="🔐 PDF Password (if required)",
            font=ctk.CTkFont(size=16, weight="bold"),  # Reduced from 18
            anchor="w",
        )
        password_section_label.grid(
            row=2, column=0, columnspan=3, sticky="w", padx=30, pady=(15, 10)
        )  # Adjusted padding

        # Password entry
        self.password_entry = ctk.CTkEntry(
            content_frame,
            textvariable=self.password,
            placeholder_text="Enter password if PDF is protected...",
            show="*",
            height=40,  # Reduced from 45
            font=ctk.CTkFont(size=13),  # Increased from 12
            corner_radius=8,
        )
        self.password_entry.grid(
            row=3, column=0, columnspan=3, sticky="ew", padx=30, pady=(0, 20)
        )  # Reduced padding

        # Process button
        self.process_btn = ctk.CTkButton(
            content_frame,
            text="🔄 Process PDF & Save CSV",
            command=self.process_pdf,
            height=45,  # Reduced from 55
            font=ctk.CTkFont(size=15, weight="bold"),  # Reduced from 16
            corner_radius=10,
            hover_color=("#1f538d", "#14375e"),
        )
        self.process_btn.grid(
            row=4, column=0, columnspan=3, sticky="ew", padx=30, pady=(0, 20)
        )  # Reduced padding
        # Status section
        status_frame = ctk.CTkFrame(
            main_frame, corner_radius=15, height=105
        )  # Increased height slightly
        status_frame.grid(row=2, column=0, sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)
        status_frame.grid_propagate(False)

        status_label = ctk.CTkLabel(
            status_frame,
            text="Status:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
            justify="left",  # Ensure left alignment
        )
        status_label.grid(row=0, column=0, sticky="w", padx=20, pady=(10, 5))

        self.status_display = ctk.CTkLabel(
            status_frame,
            textvariable=self.status_text,
            font=ctk.CTkFont(size=14),
            anchor="w",
            justify="left",  # Ensure left alignment
            wraplength=status_frame.winfo_width() or 1,  # Initial value, will update after layout
            text_color=("gray30", "gray70"),
        )

        # Make wraplength responsive to frame width
        def update_wraplength(event=None):
            # Subtract some padding if needed (e.g., 40px)
            self.status_display.configure(wraplength=max(status_frame.winfo_width() - 40, 100))

        status_frame.bind("<Configure>", update_wraplength)
        self.status_display.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 10))

    def browse_file(self):
        """Open file dialog to select PDF file"""
        file_path = filedialog.askopenfilename(
            title="Select CAMS PDF Statement",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialdir=os.path.expanduser("~"),
        )

        if file_path:
            self.selected_file.set(file_path)
            self.update_status(f"Selected: {Path(file_path).name}", "info")

    def process_pdf(self):
        """Process the selected PDF file"""
        if not self.selected_file.get():
            self.show_error("Please select a PDF file first.")
            return

        if not os.path.exists(self.selected_file.get()):
            self.show_error("Selected file does not exist.")
            return

        # Update status to show processing
        self.update_status("Processing PDF file...", "processing")
        self.process_btn.configure(state="disabled")
        self.root.update()

        # Start processing in a separate thread
        thread = threading.Thread(
            target=self._process_pdf_thread,
            args=(self.selected_file.get(), self.password.get() or None),
        )
        thread.daemon = True
        thread.start()

    def _process_pdf_thread(self, pdf_file_path, pdf_password):
        """Background thread for PDF processing"""
        try:
            processed_data, status_msg = extract_transactions_from_pdf(
                pdf_file_path, pdf_password
            )

            if status_msg == "Success" and processed_data:
                csv_string_content = convert_to_csv_string(processed_data)
                if not csv_string_content:
                    self.root.after(
                        0,
                        self._handle_processing_error,
                        "Failed to generate CSV content.",
                    )
                    return

                # Generate output filename
                now = datetime.now()
                timestamp_str = now.strftime("%d%m%Y_%H_%M_%S")
                base_pdf_name = os.path.splitext(os.path.basename(pdf_file_path))[0]
                safe_base_pdf_name = "".join(
                    c if c.isalnum() else "_" for c in base_pdf_name
                )
                csv_filename = f"{safe_base_pdf_name}_transactions_{timestamp_str}.csv"
                csv_filepath = os.path.join(self.GENERATED_CSVS_FOLDER, csv_filename)

                # Save CSV
                with open(csv_filepath, "w", encoding="utf-8", newline="") as f:
                    f.write(csv_string_content)

                self.root.after(0, self._handle_processing_success, csv_filepath)
            else:
                self.root.after(0, self._handle_processing_error, status_msg)

        except Exception as e:
            print("--- UNEXPECTED ERROR IN PDF PROCESSING ---")
            traceback.print_exc()
            print("----------------------------------------")
            self.root.after(0, self._handle_processing_error, str(e))

    def _handle_processing_success(self, csv_filepath):
        """Handle successful PDF processing"""
        self.process_btn.configure(state="normal")
        self.password_entry.delete(0, "end")
        self.update_status(
            f"✅ Success!! - CSV File saved as {os.path.basename(csv_filepath)} \n Location: {csv_filepath}",
            "success",
        )

    def _handle_processing_error(self, error_message):
        """Handle PDF processing error"""
        self.process_btn.configure(state="normal")
        self.password_entry.delete(0, "end")
        self.show_error(error_message)

    def update_status(self, message, status_type="info"):
        """Update status message with appropriate color"""
        self.status_text.set(message)

        if status_type == "success":
            self.status_display.configure(text_color="#00FF00")  # Bright green
        elif status_type == "error":
            self.status_display.configure(text_color="#FF3333")  # Bright red
        elif status_type == "processing":
            self.status_display.configure(text_color="#FFD700")  # Gold yellow
        else:
            self.status_display.configure(text_color=("gray30", "gray70"))

    def show_error(self, message):
        """Show error message and update status"""
        self.update_status(f"❌ Error: {message}", "error")
        messagebox.showerror("Error", message)

    def run(self):
        """Start the application"""
        self.root.mainloop()


# Create and run the application
if __name__ == "__main__":
    app = CAMSProcessorApp()
    app.run()
