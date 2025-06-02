import os
import sys
import traceback
import threading  # Import the threading module
from datetime import datetime  # For generating unique filenames
from tkinter import (
    filedialog,
    messagebox,
)  # Import filedialog for the 'open file' dialog
import customtkinter as ctk  # Import the CustomTkinter library

# To check if running as a script or bundled app
# --- Import your PDF parsing functions ---
# Make sure cams_parser.py is in the same directory as gui_app.py
# or adjust the import path accordingly if it's in a sub-module.
try:
    from cams_parser import extract_transactions_from_pdf, convert_to_csv_string
except ImportError:
    messagebox.showerror(
        "Import Error",
        "Could not import 'cams_parser.py'. Make sure it's in the same directory.",
    )
    sys.exit()  # Exit if the parser can't be imported


# --- Main Application Class (Optional but good practice for larger GUIs) ---
# For now, we'll keep it simple and build directly.
# If the app grows, encapsulating it in a class is better.

# --- GUI Setup ---
# Set the appearance mode and default color theme for CustomTkinter.
# "System" will adapt to the user's OS theme (light/dark).
# Other modes: "Light", "Dark"
ctk.set_appearance_mode("System")
# Other themes: "green", "dark-blue"
ctk.set_default_color_theme("blue")

# Create the main application window (often called 'app' or 'root')
app = ctk.CTk()
app.title("CAMS PDF Statement Processor")  # Set the title of the window
app.geometry("600x350")  # Set the initial size of the window (width x height)

# --- Global variable to store the selected file path ---
# We use a CTkinter StringVar so the Entry widget can be easily updated
selected_pdf_path_var = ctk.StringVar()
status_message_var = ctk.StringVar(value="Status: Ready")  # Initialize status message

# --- Define output directory ---
# Get the directory where the script (or executable) is running
if getattr(sys, "frozen", False):  # Running as a bundled app (e.g., PyInstaller)
    application_path = os.path.dirname(sys.executable)
else:  # Running as a normal script
    application_path = os.path.dirname(__file__)

GENERATED_CSVS_FOLDER = os.path.join(application_path, "generated_csvs")
os.makedirs(GENERATED_CSVS_FOLDER, exist_ok=True)  # Ensure the folder exists


# --- Event Handler Functions ---
def browse_file():
    """
    Opens a file dialog for the user to select a PDF file.
    Updates the file path entry field with the selected file.
    """
    # askopenfilename opens the "Open file" dialog
    # filetypes limits the displayed files to PDF and All files
    # initialdir can be set to a default directory, e.g., os.path.expanduser("~") for home
    file_path = filedialog.askopenfilename(
        title="Select PDF Statement File",
        filetypes=(("PDF files", "*.pdf"), ("All files", "*.*")),
    )
    if file_path:  # If the user selected a file (and didn't cancel)
        selected_pdf_path_var.set(
            file_path
        )  # Update the StringVar, which updates the Entry widget
        status_message_var.set(
            f"File: {os.path.basename(file_path)}"
        )  # Update status message with the selected file name
    else:
        if selected_pdf_path_var.get():
            selected_pdf_path_var.set("")  # Clear the entry if no file was selected
        status_message_var.set("Status: No file selected.")  # Update status message


def actual_pdf_processing_task(pdf_file_path, pdf_password):
    """
    This function contains the long-running PDF processing logic.
    It will be executed in a separate thread.
    It returns the processed data (list of dicts) and a status message.
    CSV string conversion and saving will be handled after this in the GUI thread..
    """
    try:
        # extract_transactions_from_pdf now returns (list_of_data, status_message)
        processed_data, status_msg_from_parser = extract_transactions_from_pdf(
            pdf_file_path, pdf_password
        )

        if status_msg_from_parser == "Success" and processed_data:
            csv_string_content = convert_to_csv_string(processed_data)
            if not csv_string_content:
                return None, "Error: Failed to generate CSV content."  # Return error

            now = datetime.now()
            timestamp_str = now.strftime("%d%m%Y_%H_%M_%S")
            base_pdf_name = os.path.splitext(os.path.basename(pdf_file_path))[0]
            safe_base_pdf_name = "".join(
                c if c.isalnum() else "_" for c in base_pdf_name
            )
            csv_filename_only = f"{safe_base_pdf_name}_transactions_{timestamp_str}.csv"
            csv_filepath_on_server = os.path.join(
                GENERATED_CSVS_FOLDER, csv_filename_only
            )

            with open(csv_filepath_on_server, "w", encoding="utf-8", newline="") as f:
                f.write(csv_string_content)

            return csv_filepath_on_server, "Success"  # Return path and success
        else:
            return None, status_msg_from_parser  # Return error from parser

    except Exception as e:
        print(
            "--- UNEXPECTED ERROR IN actual_pdf_processing_task (background thread) ---"
        )
        traceback.print_exc()
        print("-----------------------------------------------------------------------")
        return None, f"Unexpected error in processing: {str(e)}"


def handle_processing_results(csv_filepath, status_msg):
    """
    This function is called by app.after() and runs in the main GUI thread.
    It updates the GUI based on the results from the background thread.
    """
    process_btn.configure(state="normal")  # Re-enable the button
    password_entry.delete(0, 'end') # Clear the password field
    if status_msg == "Success" and csv_filepath:
        messagebox.showinfo(
            "Success", f"CSV file generated successfully!\n\nSaved to:\n{csv_filepath}"
        )
        status_message_var.set(
            f"Status: Success! CSV saved as {os.path.basename(csv_filepath)}"
        )
    else:
        messagebox.showerror("Processing Error", status_msg)
        status_message_var.set(f"Status: Error - {status_msg}")


def process_pdf_action():
    """
    Handles the PDF processing when the button is clicked.
    Handles the button click. Disables the button, updates status,
    and starts the PDF processing in a new thread.
    """
    pdf_file_path = selected_pdf_path_var.get()
    password_str = password_entry.get()  # Get password directly from the entry widget

    if not pdf_file_path:
        messagebox.showerror("Error", "Please select a PDF file first.")
        status_message_var.set("Status: Error - No PDF file selected.")
        return
    # Treat empty password string from entry as None for the parser
    pdf_password = password_str if password_str else None

    status_message_var.set("Status: Processing PDF... Please wait.")
    process_btn.configure(state="disabled")  # Disable button during processing
    app.update_idletasks()  # Force GUI update to show the "Processing" message

    # Create and start the background thread
    # Pass the result handler function and its arguments to the target
    thread = threading.Thread(
        target=lambda: app.after(
            0,
            handle_processing_results,
            *actual_pdf_processing_task(pdf_file_path, pdf_password),
        )
    )
    thread.daemon = True  # Allows main program to exit even if thread is running
    thread.start()


# --- GUI Layout ---
# Create a frame to hold file selection widgets neatly
file_selection_frame = ctk.CTkFrame(master=app)
# pack the frame:
# pady=10: 10 pixels of vertical padding around the frame
# padx=10: 10 pixels of horizontal padding around the frame
# fill="x": makes the frame expand horizontally to fill available space
file_selection_frame.pack(pady=(20, 5), padx=20, fill="x")

# Create a Label for file selection
pdf_label = ctk.CTkLabel(master=file_selection_frame, text="Select PDF Statement:")
# pack the label within its frame:
pdf_label.pack(side="left", padx=(0, 5))

# Entry field to display the selected file path
# state="readonly": makes the entry field not directly editable by the user
# textvariable=selected_pdf_path_var: links this entry to the StringVar
pdf_path_entry = ctk.CTkEntry(
    master=file_selection_frame,
    textvariable=selected_pdf_path_var,
    state="readonly",
    width=350,
)
# pack the entry field:
# expand=True: allows the widget to expand if extra space is available
pdf_path_entry.pack(side="left", expand=True, fill="x", padx=5)

# Button to browse for a file
browse_btn = ctk.CTkButton(
    master=file_selection_frame, text="Browse...", command=browse_file
)
# command=browse_file: specifies the function to call when the button is clicked
browse_btn.pack(side="left", padx=(5, 0))

# --- Frame to hold the password input widgets ---
password_frame = ctk.CTkFrame(master=app)
password_frame.pack(pady=5, padx=20, fill="x")

# Label for password input
password_label = ctk.CTkLabel(master=password_frame, text="PDF Password (if any):")
password_label.pack(side="left", padx=(0, 5))

# Entry field for password input
# show="*": displays asterisks instead of the actual characters typed
password_entry = ctk.CTkEntry(master=password_frame, show="*", width=250)
password_entry.pack(side="left", padx=5)
# You can pre-fill it if needed, e.g., password_entry.insert(0, "default_password")
# For now, it will be empty by default.

# --Process Button ---
process_btn = ctk.CTkButton(
    master=app, text="Process PDF & Save CSV", command=process_pdf_action
)
process_btn.pack(pady=20)

# --- Status Label ---
status_label = ctk.CTkLabel(master=app, textvariable=status_message_var)
status_label.pack(pady=(0, 10), padx=20, fill="x")


# --- Start the Tkinter event loop ---
# This line is essential; it keeps the window open and responsive to user interactions.
# It should always be the last line of your GUI setup.
app.mainloop()
