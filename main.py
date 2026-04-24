from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from uuid import uuid4


DATA_FILE = Path(__file__).with_name("clinic_data.json")
USERS_FILE = Path(__file__).with_name("users.json")
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "1234"


@dataclass
class Patient:
    id: str
    full_name: str
    age: str
    phone: str
    gender: str
    notes: str


@dataclass
class Appointment:
    id: str
    patient_id: str
    doctor: str
    date: str
    time: str
    status: str
    reason: str


class ClinicStorage:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.patients: list[Patient] = []
        self.appointments: list[Appointment] = []
        self.load()

    def load(self) -> None:
        if not self.file_path.exists():
            self.save()
            return

        with self.file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        self.patients = [self._deserialize_patient(item) for item in data.get("patients", [])]
        self.appointments = [Appointment(**item) for item in data.get("appointments", [])]

    def save(self) -> None:
        payload = {
            "patients": [asdict(patient) for patient in self.patients],
            "appointments": [asdict(appointment) for appointment in self.appointments],
        }
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    @staticmethod
    def _deserialize_patient(item: dict[str, str]) -> Patient:
        if "full_name" not in item and "name" in item:
            item = {**item, "full_name": item["name"]}
        return Patient(**item)


class UserStorage:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.users: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        if not self.file_path.exists():
            self.users = {DEFAULT_USERNAME: DEFAULT_PASSWORD}
            self.save()
            return

        with self.file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        self.users = data.get("users", {})
        if not self.users:
            self.users = {DEFAULT_USERNAME: DEFAULT_PASSWORD}
            self.save()

    def save(self) -> None:
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump({"users": self.users}, file, ensure_ascii=False, indent=2)

    def validate(self, username: str, password: str) -> bool:
        return self.users.get(username) == password

    def add_user(self, username: str, password: str) -> bool:
        if username in self.users:
            return False
        self.users[username] = password
        self.save()
        return True


class ClinicApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Simple Clinic System")
        self.root.geometry("1080x700")
        self.root.minsize(960, 620)
        self.root.configure(bg="#eef5f3")

        self.storage = ClinicStorage(DATA_FILE)
        self.selected_patient_id: str | None = None
        self.selected_appointment_id: str | None = None

        self.search_var = tk.StringVar()
        self.patient_name_var = tk.StringVar()
        self.patient_age_var = tk.StringVar()
        self.patient_phone_var = tk.StringVar()
        self.patient_gender_var = tk.StringVar(value="Male")

        self.appointment_patient_var = tk.StringVar()
        self.appointment_doctor_var = tk.StringVar()
        self.appointment_date_var = tk.StringVar()
        self.appointment_time_var = tk.StringVar()
        self.appointment_status_var = tk.StringVar(value="Scheduled")

        self.stats_var = tk.StringVar()

        self._configure_style()
        self._build_ui()
        self.refresh_all_views()

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        background = "#eef5f3"
        surface = "#ffffff"
        primary = "#1f5c5b"
        accent = "#2d8f85"
        accent_hover = "#256f68"
        soft = "#dcefea"
        text = "#20323a"
        muted = "#5d7478"

        style.configure("TFrame", background=background)
        style.configure("TLabelframe", background=surface, borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", background=surface, foreground=primary, font=("Segoe UI Semibold", 11))
        style.configure("TLabel", background=surface, foreground=text, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=background, foreground=primary, font=("Segoe UI Semibold", 18))
        style.configure("Stats.TLabel", background=background, foreground=muted, font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=6, background=soft)
        style.map("TButton", background=[("active", "#cfe5df")])
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=6, background=accent, foreground="white")
        style.map("Accent.TButton", background=[("active", accent_hover)])
        style.configure("TNotebook", background=background, borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI Semibold", 10), padding=(14, 8), background=soft, foreground=primary)
        style.map("TNotebook.Tab", background=[("selected", surface)], foreground=[("selected", primary)])
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10), background=surface, fieldbackground=surface)
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10), background=soft, foreground=primary)
        style.map("Treeview", background=[("selected", "#cfe7e2")], foreground=[("selected", text)])

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=14)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Simple Clinic System", style="Header.TLabel").pack(anchor="w")
        ttk.Label(container, textvariable=self.stats_var, style="Stats.TLabel").pack(anchor="w", pady=(4, 12))

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True)

        patients_tab = ttk.Frame(notebook, padding=12)
        appointments_tab = ttk.Frame(notebook, padding=12)
        notebook.add(patients_tab, text="Patients")
        notebook.add(appointments_tab, text="Appointments")

        self._build_patients_tab(patients_tab)
        self._build_appointments_tab(appointments_tab)

    def _build_patients_tab(self, parent: ttk.Frame) -> None:
        form = ttk.LabelFrame(parent, text="Patient Form", padding=12)
        form.pack(fill="x")

        ttk.Label(form, text="Full Name").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(form, textvariable=self.patient_name_var, width=24).grid(row=0, column=1, padx=4, pady=4)

        ttk.Label(form, text="Age").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(form, textvariable=self.patient_age_var, width=12).grid(row=0, column=3, padx=4, pady=4)

        ttk.Label(form, text="Phone").grid(row=0, column=4, sticky="w", padx=4, pady=4)
        ttk.Entry(form, textvariable=self.patient_phone_var, width=20).grid(row=0, column=5, padx=4, pady=4)

        ttk.Label(form, text="Gender").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Combobox(form, textvariable=self.patient_gender_var, values=["Male", "Female"], state="readonly", width=21).grid(
            row=1, column=1, padx=4, pady=4
        )

        ttk.Label(form, text="Notes").grid(row=1, column=2, sticky="nw", padx=4, pady=4)
        self.patient_notes_text = tk.Text(
            form,
            width=48,
            height=4,
            font=("Segoe UI", 10),
            bg="#fbfefd",
            fg="#20323a",
            insertbackground="#20323a",
            relief="solid",
            bd=1,
        )
        self.patient_notes_text.grid(row=1, column=3, columnspan=3, padx=4, pady=4, sticky="ew")

        buttons = ttk.Frame(form)
        buttons.grid(row=2, column=0, columnspan=6, sticky="w", pady=(8, 0))
        ttk.Button(buttons, text="Add", style="Accent.TButton", command=self.add_patient).pack(side="left", padx=4)
        ttk.Button(buttons, text="Update", command=self.update_patient).pack(side="left", padx=4)
        ttk.Button(buttons, text="Delete", command=self.delete_patient).pack(side="left", padx=4)
        ttk.Button(buttons, text="Clear", command=self.clear_patient_form).pack(side="left", padx=4)

        search_row = ttk.Frame(parent, padding=(0, 12, 0, 8))
        search_row.pack(fill="x")
        ttk.Label(search_row, text="Search").pack(side="left")
        search_entry = ttk.Entry(search_row, textvariable=self.search_var, width=28)
        search_entry.pack(side="left", padx=8)
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_patient_views())

        columns = ("full_name", "age", "phone", "gender")
        self.patient_tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)
        for column, title, width in (
            ("full_name", "Full Name", 280),
            ("age", "Age", 80),
            ("phone", "Phone", 180),
            ("gender", "Gender", 100),
        ):
            self.patient_tree.heading(column, text=title)
            self.patient_tree.column(column, width=width, anchor="center" if column != "full_name" else "w")
        self.patient_tree.pack(fill="both", expand=True)
        self.patient_tree.bind("<<TreeviewSelect>>", self.on_patient_select)

    def _build_appointments_tab(self, parent: ttk.Frame) -> None:
        form = ttk.LabelFrame(parent, text="Appointment Form", padding=12)
        form.pack(fill="x")

        ttk.Label(form, text="Patient").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.patient_combo = ttk.Combobox(form, textvariable=self.appointment_patient_var, state="readonly", width=28)
        self.patient_combo.grid(row=0, column=1, padx=4, pady=4)

        ttk.Label(form, text="Doctor").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(form, textvariable=self.appointment_doctor_var, width=20).grid(row=0, column=3, padx=4, pady=4)

        ttk.Label(form, text="Date").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(form, textvariable=self.appointment_date_var, width=20).grid(row=1, column=1, padx=4, pady=4)

        ttk.Label(form, text="Time").grid(row=1, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(form, textvariable=self.appointment_time_var, width=20).grid(row=1, column=3, padx=4, pady=4)

        ttk.Label(form, text="Status").grid(row=0, column=4, sticky="w", padx=4, pady=4)
        ttk.Combobox(
            form,
            textvariable=self.appointment_status_var,
            values=["Scheduled", "Completed", "Cancelled"],
            state="readonly",
            width=18,
        ).grid(row=0, column=5, padx=4, pady=4)

        ttk.Label(form, text="Reason").grid(row=1, column=4, sticky="nw", padx=4, pady=4)
        self.appointment_reason_text = tk.Text(
            form,
            width=28,
            height=4,
            font=("Segoe UI", 10),
            bg="#fbfefd",
            fg="#20323a",
            insertbackground="#20323a",
            relief="solid",
            bd=1,
        )
        self.appointment_reason_text.grid(row=1, column=5, padx=4, pady=4)

        buttons = ttk.Frame(form)
        buttons.grid(row=2, column=0, columnspan=6, sticky="w", pady=(8, 0))
        ttk.Button(buttons, text="Add", style="Accent.TButton", command=self.add_appointment).pack(side="left", padx=4)
        ttk.Button(buttons, text="Update", command=self.update_appointment).pack(side="left", padx=4)
        ttk.Button(buttons, text="Delete", command=self.delete_appointment).pack(side="left", padx=4)
        ttk.Button(buttons, text="Done", command=self.mark_appointment_done).pack(side="left", padx=4)
        ttk.Button(buttons, text="Clear", command=self.clear_appointment_form).pack(side="left", padx=4)

        columns = ("patient", "doctor", "date", "time", "status")
        self.appointment_tree = ttk.Treeview(parent, columns=columns, show="headings", height=16)
        for column, title, width in (
            ("patient", "Patient", 250),
            ("doctor", "Doctor", 170),
            ("date", "Date", 120),
            ("time", "Time", 100),
            ("status", "Status", 110),
        ):
            self.appointment_tree.heading(column, text=title)
            self.appointment_tree.column(column, width=width, anchor="center" if column != "patient" and column != "doctor" else "w")
        self.appointment_tree.pack(fill="both", expand=True, pady=(12, 0))
        self.appointment_tree.bind("<<TreeviewSelect>>", self.on_appointment_select)

    def add_patient(self) -> None:
        if not self.patient_name_var.get().strip():
            messagebox.showwarning("Missing Data", "Full name is required.")
            return

        patient = Patient(
            id=str(uuid4()),
            full_name=self.patient_name_var.get().strip(),
            age=self.patient_age_var.get().strip(),
            phone=self.patient_phone_var.get().strip(),
            gender=self.patient_gender_var.get().strip(),
            notes=self.patient_notes_text.get("1.0", "end").strip(),
        )
        self.storage.patients.append(patient)
        self.persist_and_refresh()
        self.clear_patient_form()

    def update_patient(self) -> None:
        if not self.selected_patient_id:
            messagebox.showwarning("Selection Required", "Choose a patient first.")
            return

        patient = self.get_patient_by_id(self.selected_patient_id)
        if patient is None:
            return

        if not self.patient_name_var.get().strip():
            messagebox.showwarning("Missing Data", "Full name is required.")
            return

        patient.full_name = self.patient_name_var.get().strip()
        patient.age = self.patient_age_var.get().strip()
        patient.phone = self.patient_phone_var.get().strip()
        patient.gender = self.patient_gender_var.get().strip()
        patient.notes = self.patient_notes_text.get("1.0", "end").strip()
        self.persist_and_refresh()

    def delete_patient(self) -> None:
        if not self.selected_patient_id:
            messagebox.showwarning("Selection Required", "Choose a patient first.")
            return

        if not messagebox.askyesno("Confirm", "Delete this patient and all related appointments?"):
            return

        self.storage.patients = [patient for patient in self.storage.patients if patient.id != self.selected_patient_id]
        self.storage.appointments = [
            appointment for appointment in self.storage.appointments if appointment.patient_id != self.selected_patient_id
        ]
        self.persist_and_refresh()
        self.clear_patient_form()
        self.clear_appointment_form()

    def add_appointment(self) -> None:
        patient_id = self._selected_patient_id_from_combo()
        if not patient_id:
            messagebox.showwarning("Missing Data", "Select a patient.")
            return

        if not self._validate_appointment_fields():
            return

        appointment = Appointment(
            id=str(uuid4()),
            patient_id=patient_id,
            doctor=self.appointment_doctor_var.get().strip(),
            date=self.appointment_date_var.get().strip(),
            time=self.appointment_time_var.get().strip(),
            status=self.appointment_status_var.get().strip(),
            reason=self.appointment_reason_text.get("1.0", "end").strip(),
        )
        self.storage.appointments.append(appointment)
        self.persist_and_refresh()
        self.clear_appointment_form()

    def update_appointment(self) -> None:
        if not self.selected_appointment_id:
            messagebox.showwarning("Selection Required", "Choose an appointment first.")
            return

        patient_id = self._selected_patient_id_from_combo()
        if not patient_id:
            messagebox.showwarning("Missing Data", "Select a patient.")
            return

        if not self._validate_appointment_fields():
            return

        appointment = self.get_appointment_by_id(self.selected_appointment_id)
        if appointment is None:
            return

        appointment.patient_id = patient_id
        appointment.doctor = self.appointment_doctor_var.get().strip()
        appointment.date = self.appointment_date_var.get().strip()
        appointment.time = self.appointment_time_var.get().strip()
        appointment.status = self.appointment_status_var.get().strip()
        appointment.reason = self.appointment_reason_text.get("1.0", "end").strip()
        self.persist_and_refresh()

    def delete_appointment(self) -> None:
        if not self.selected_appointment_id:
            messagebox.showwarning("Selection Required", "Choose an appointment first.")
            return

        self.storage.appointments = [
            appointment for appointment in self.storage.appointments if appointment.id != self.selected_appointment_id
        ]
        self.persist_and_refresh()
        self.clear_appointment_form()

    def mark_appointment_done(self) -> None:
        if not self.selected_appointment_id:
            messagebox.showwarning("Selection Required", "Choose an appointment first.")
            return

        appointment = self.get_appointment_by_id(self.selected_appointment_id)
        if appointment is None:
            return

        appointment.status = "Completed"
        self.persist_and_refresh()

    def on_patient_select(self, _event: object) -> None:
        selection = self.patient_tree.selection()
        if not selection:
            return

        patient = self.get_patient_by_id(selection[0])
        if patient is None:
            return

        self.selected_patient_id = patient.id
        self.patient_name_var.set(patient.full_name)
        self.patient_age_var.set(patient.age)
        self.patient_phone_var.set(patient.phone)
        self.patient_gender_var.set(patient.gender)
        self.patient_notes_text.delete("1.0", "end")
        self.patient_notes_text.insert("1.0", patient.notes)

    def on_appointment_select(self, _event: object) -> None:
        selection = self.appointment_tree.selection()
        if not selection:
            return

        appointment = self.get_appointment_by_id(selection[0])
        if appointment is None:
            return

        patient = self.get_patient_by_id(appointment.patient_id)
        self.selected_appointment_id = appointment.id
        self.appointment_patient_var.set(self._patient_combo_label(patient) if patient else "")
        self.appointment_doctor_var.set(appointment.doctor)
        self.appointment_date_var.set(appointment.date)
        self.appointment_time_var.set(appointment.time)
        self.appointment_status_var.set(appointment.status)
        self.appointment_reason_text.delete("1.0", "end")
        self.appointment_reason_text.insert("1.0", appointment.reason)

    def refresh_all_views(self) -> None:
        self.refresh_patient_views()
        self.refresh_appointment_views()
        self.refresh_stats()

    def refresh_patient_views(self) -> None:
        query = self.search_var.get().strip().lower()
        self.patient_tree.delete(*self.patient_tree.get_children())

        for patient in sorted(self.storage.patients, key=lambda item: item.full_name.lower()):
            if query and query not in f"{patient.full_name} {patient.phone}".lower():
                continue
            self.patient_tree.insert("", "end", iid=patient.id, values=(patient.full_name, patient.age, patient.phone, patient.gender))

        self.patient_combo["values"] = [self._patient_combo_label(patient) for patient in self.storage.patients]

    def refresh_appointment_views(self) -> None:
        self.appointment_tree.delete(*self.appointment_tree.get_children())

        for appointment in sorted(self.storage.appointments, key=lambda item: (item.date, item.time)):
            patient = self.get_patient_by_id(appointment.patient_id)
            patient_name = patient.full_name if patient else "Deleted patient"
            self.appointment_tree.insert(
                "",
                "end",
                iid=appointment.id,
                values=(patient_name, appointment.doctor, appointment.date, appointment.time, appointment.status),
            )

    def refresh_stats(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        total_patients = len(self.storage.patients)
        total_appointments = len(self.storage.appointments)
        today_appointments = sum(1 for item in self.storage.appointments if item.date == today)
        self.stats_var.set(
            f"Patients: {total_patients}    Appointments: {total_appointments}    Today: {today_appointments}"
        )

    def persist_and_refresh(self) -> None:
        self.storage.save()
        self.refresh_all_views()

    def clear_patient_form(self) -> None:
        self.selected_patient_id = None
        self.patient_name_var.set("")
        self.patient_age_var.set("")
        self.patient_phone_var.set("")
        self.patient_gender_var.set("Male")
        self.patient_notes_text.delete("1.0", "end")
        self.patient_tree.selection_remove(self.patient_tree.selection())

    def clear_appointment_form(self) -> None:
        self.selected_appointment_id = None
        self.appointment_patient_var.set("")
        self.appointment_doctor_var.set("")
        self.appointment_date_var.set("")
        self.appointment_time_var.set("")
        self.appointment_status_var.set("Scheduled")
        self.appointment_reason_text.delete("1.0", "end")
        self.appointment_tree.selection_remove(self.appointment_tree.selection())

    def get_patient_by_id(self, patient_id: str) -> Patient | None:
        return next((patient for patient in self.storage.patients if patient.id == patient_id), None)

    def get_appointment_by_id(self, appointment_id: str) -> Appointment | None:
        return next((appointment for appointment in self.storage.appointments if appointment.id == appointment_id), None)

    def _selected_patient_id_from_combo(self) -> str | None:
        selected = self.appointment_patient_var.get().strip()
        if not selected:
            return None
        patient_id = selected.split(" | ")[0]
        return patient_id if self.get_patient_by_id(patient_id) else None

    def _patient_combo_label(self, patient: Patient) -> str:
        return f"{patient.id} | {patient.full_name}"

    def _validate_appointment_fields(self) -> bool:
        if not self.appointment_doctor_var.get().strip():
            messagebox.showwarning("Missing Data", "Doctor name is required.")
            return False

        try:
            datetime.strptime(self.appointment_date_var.get().strip(), "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid Date", "Use date format YYYY-MM-DD.")
            return False

        try:
            datetime.strptime(self.appointment_time_var.get().strip(), "%H:%M")
        except ValueError:
            messagebox.showerror("Invalid Time", "Use time format HH:MM.")
            return False

        return True


class LoginWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Login")
        self.root.geometry("460x360")
        self.root.minsize(420, 320)
        self.root.configure(bg="#eef5f3")
        self.user_storage = UserStorage(USERS_FILE)

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.register_username_var = tk.StringVar()
        self.register_password_var = tk.StringVar()
        self.confirm_password_var = tk.StringVar()

        self._configure_style()
        self._build_ui()

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Login.TFrame", background="#eef5f3")
        style.configure("LoginCard.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("LoginTitle.TLabel", background="#ffffff", foreground="#1f5c5b", font=("Segoe UI Semibold", 18))
        style.configure("LoginHint.TLabel", background="#ffffff", foreground="#5d7478", font=("Segoe UI", 10))
        style.configure("LoginField.TLabel", background="#ffffff", foreground="#20323a", font=("Segoe UI", 10))
        style.configure(
            "LoginButton.TButton",
            font=("Segoe UI Semibold", 10),
            padding=7,
            background="#2d8f85",
            foreground="white",
        )
        style.map("LoginButton.TButton", background=[("active", "#256f68")])

    def _build_ui(self) -> None:
        wrapper = ttk.Frame(self.root, style="Login.TFrame", padding=24)
        wrapper.pack(fill="both", expand=True)

        card = ttk.Frame(wrapper, style="LoginCard.TFrame", padding=22)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="Clinic Access", style="LoginTitle.TLabel").pack(anchor="center")
        ttk.Label(card, text="Login or create a new account.", style="LoginHint.TLabel").pack(
            anchor="center", pady=(4, 18)
        )

        notebook = ttk.Notebook(card)
        notebook.pack(fill="both", expand=True)

        login_tab = ttk.Frame(notebook, padding=12)
        register_tab = ttk.Frame(notebook, padding=12)
        notebook.add(login_tab, text="Login")
        notebook.add(register_tab, text="Register")

        ttk.Label(login_tab, text="Username", style="LoginField.TLabel").pack(anchor="w")
        username_entry = ttk.Entry(login_tab, textvariable=self.username_var, width=30)
        username_entry.pack(fill="x", pady=(4, 12))

        ttk.Label(login_tab, text="Password", style="LoginField.TLabel").pack(anchor="w")
        password_entry = ttk.Entry(login_tab, textvariable=self.password_var, show="*", width=30)
        password_entry.pack(fill="x", pady=(4, 16))

        ttk.Button(login_tab, text="Login", style="LoginButton.TButton", command=self.attempt_login).pack(fill="x")
        ttk.Label(
            login_tab,
            text=f"Default account: {DEFAULT_USERNAME} / {DEFAULT_PASSWORD}",
            style="LoginHint.TLabel",
        ).pack(anchor="center", pady=(14, 0))

        ttk.Label(register_tab, text="New Username", style="LoginField.TLabel").pack(anchor="w")
        ttk.Entry(register_tab, textvariable=self.register_username_var, width=30).pack(fill="x", pady=(4, 12))

        ttk.Label(register_tab, text="New Password", style="LoginField.TLabel").pack(anchor="w")
        ttk.Entry(register_tab, textvariable=self.register_password_var, show="*", width=30).pack(fill="x", pady=(4, 12))

        ttk.Label(register_tab, text="Confirm Password", style="LoginField.TLabel").pack(anchor="w")
        ttk.Entry(register_tab, textvariable=self.confirm_password_var, show="*", width=30).pack(fill="x", pady=(4, 16))

        ttk.Button(register_tab, text="Create Account", style="LoginButton.TButton", command=self.register_user).pack(
            fill="x"
        )

        username_entry.focus_set()
        self.root.bind("<Return>", lambda _event: self.attempt_login())
        self.root.bind("<Escape>", lambda _event: self.root.destroy())

    def attempt_login(self) -> None:
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        if self.user_storage.validate(username, password):
            self.root.unbind("<Return>")
            self.root.unbind("<Escape>")
            for child in self.root.winfo_children():
                child.destroy()
            ClinicApp(self.root)
            return

        messagebox.showerror("Login Failed", "Incorrect username or password.")

    def register_user(self) -> None:
        username = self.register_username_var.get().strip()
        password = self.register_password_var.get().strip()
        confirm_password = self.confirm_password_var.get().strip()

        if not username or not password:
            messagebox.showwarning("Missing Data", "Username and password are required.")
            return

        if len(password) < 4:
            messagebox.showwarning("Weak Password", "Password must be at least 4 characters.")
            return

        if password != confirm_password:
            messagebox.showerror("Password Error", "Password confirmation does not match.")
            return

        if not self.user_storage.add_user(username, password):
            messagebox.showwarning("Duplicate User", "This username already exists.")
            return

        self.username_var.set(username)
        self.password_var.set(password)
        self.register_username_var.set("")
        self.register_password_var.set("")
        self.confirm_password_var.set("")
        messagebox.showinfo("Account Created", "New account created successfully. You can login now.")


def main() -> None:
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
