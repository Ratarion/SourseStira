# --- СЛОВАРЬ ЛОКАЛИЗАЦИИ ---
ENtexts = {
    "ENG": { # Изменено с "ENG" на "ENG" - это был опечатка, но проверим.
        "hello_user": "Hello, {name}! Choose an action:",
        "welcome_lang_choice": "Hello, choose a language",
        "record_laundry": "Book a wash",
        "show_records": "Show my bookings",
        "cancel_record": "Cancel booking",
        "exit": "Exit",
        "back": "Back",
        "machine_type": "Machine",
        # Registration
        "reg_start": "Hello! Let's register.\n\nPlease enter your <b>Full Name</b> separated by spaces:\n<i>Example: Smith John David</i>",
        "reg_fio_error": "Please enter your Last Name, First Name, and Middle Name separated by spaces.",
        "reg_room_prompt": "Accepted! Now enter your <b>room number</b> (digits only):",
        "reg_room_error": "The room number must be a digit.",
        "reg_id_prompt": "Enter your <b>student ID number</b>:",
        "reg_id_error": "The student ID must be a digit.",
        "reg_success": "Registration successful! Welcome.",
        "reg_db_error": "Error during saving: ",
        # Booking
        "record_start": "Select a date (function under development)",
        "slots_none": "No free slots available on {date}",
        "time_prompt": "Select a time for {date}:",
        "machines_none": "Oops! All machines are busy at this time.",
        "machine_prompt": "Select a washing machine for {datetime}:",
        "booking_success": "Booking created!\nMachine №{machine_num}\n{start} – {end}",
        "booking_error": "The slot is already taken by another user!",
    }
}